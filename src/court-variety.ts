/**
 * Court Variety and Mix Tracking System
 * 
 * Key Features:
 * 1. HARD CAP: Same courts NEVER mix 2x in a row
 * 2. Waitlist as Court: Treated as virtual court (floor(waitlistSize / 4))
 * 3. Finish Balancing: Track which courts finish, balance usage
 * 4. Variety Thresholds: Adaptive (0-100) for each court
 */

import type { Session, CourtVarietyState, CourtMixHistory } from './types';

// Special court number for waitlist
const WAITLIST_COURT_NUMBER = 0;

/**
 * Initialize court variety state for a session
 */
export function initializeCourtVarietyState(totalCourts: number): CourtVarietyState {
  const courtMixes = new Map<number, CourtMixHistory>();
  
  // Add waitlist as a virtual court (court 0)
  courtMixes.set(WAITLIST_COURT_NUMBER, {
    courtNumber: WAITLIST_COURT_NUMBER,
    lastMixedWith: new Set(),
    finishCount: 0,
    varietyThreshold: 50,
  });
  
  // Add physical courts (1, 2, 3, ...)
  for (let i = 1; i <= totalCourts; i++) {
    courtMixes.set(i, {
      courtNumber: i,
      lastMixedWith: new Set(),
      finishCount: 0,
      varietyThreshold: 50,
    });
  }
  
  return {
    courtMixes,
    waitlistCourtCount: 0,
    lastMixRound: 0,
    totalCourtFinishes: new Map(
      Array.from({ length: totalCourts + 1 }, (_, i) => [i, 0])
    ),
  };
}

/**
 * Record when a court finishes a match
 */
export function recordCourtFinish(
  session: Session,
  courtNumber: number
): void {
  const state = session.courtVarietyState;
  
  if (!state.courtMixes.has(courtNumber)) {
    return;
  }
  
  const courtData = state.courtMixes.get(courtNumber)!;
  courtData.finishCount++;
  
  const totalFinishes = state.totalCourtFinishes.get(courtNumber) || 0;
  state.totalCourtFinishes.set(courtNumber, totalFinishes + 1);
}

/**
 * HARD CAP: Record which courts mixed in this round
 * Returns true if successful, false if HARD CAP would be violated
 * 
 * CRITICAL: The waitlist (Court 0) accumulates history across multiple mixes in the same round.
 * This prevents the same physical courts from mixing with the waitlist repeatedly.
 */
export function recordCourtMix(
  session: Session,
  courtsInvolved: number[]
): boolean {
  const state = session.courtVarietyState;
  
  // HARD CAP CHECK: Courts cannot use the same combination twice in a row
  if (courtsInvolved.length > 0 && state.lastMixRound > 0) {
    // Only check HARD CAP if we've already done at least one round
    const allMixedLastRound = courtsInvolved.every(courtNum => {
      const courtData = state.courtMixes.get(courtNum);
      if (!courtData) return false;
      
      // Check if this court mixed with ALL other courts in proposed mix
      return courtsInvolved.every(other => 
        other === courtNum || courtData.lastMixedWith.has(other)
      );
    });
    
    if (allMixedLastRound && courtsInvolved.length > 0) {
      // HARD CAP VIOLATION: Same courts cannot mix again
      return false;
    }
  }
  
  // IMPORTANT: Only clear lastMixedWith for NON-WAITLIST courts that are currently mixing
  // This allows multiple matches to be created in the same evaluation without
  // interfering with each other's mix history
  // CRITICAL: Keep the waitlist court's history intact - it accumulates during the round
  courtsInvolved.forEach(courtNum => {
    if (courtNum !== 0) { // Don't clear waitlist history
      const courtData = state.courtMixes.get(courtNum);
      if (courtData) {
        courtData.lastMixedWith.clear();
      }
    }
  });
  
  // Record this mix
  courtsInvolved.forEach(courtNum => {
    const courtData = state.courtMixes.get(courtNum);
    if (courtData) {
      courtsInvolved.forEach(otherCourtNum => {
        if (otherCourtNum !== courtNum) {
          courtData.lastMixedWith.add(otherCourtNum);
        }
      });
    }
  });
  
  state.lastMixRound++;
  return true;
}

/**
 * Update variety thresholds for physical courts
 */
export function updateVarietyThresholds(session: Session): void {
  const state = session.courtVarietyState;
  
  // Get finish counts for physical courts only
  const physicalCourts = Array.from(state.totalCourtFinishes.entries())
    .filter(([courtNum]) => courtNum !== WAITLIST_COURT_NUMBER);
  
  if (physicalCourts.length === 0) return;
  
  const finishCounts = physicalCourts.map(([, count]) => count);
  const avgFinishes = finishCounts.reduce((a, b) => a + b, 0) / finishCounts.length;
  
  // Adjust thresholds based on imbalance
  state.courtMixes.forEach((court, courtNum) => {
    // Skip waitlist
    if (courtNum === WAITLIST_COURT_NUMBER) return;
    
    const courtFinishes = state.totalCourtFinishes.get(courtNum) || 0;
    
    if (courtFinishes < avgFinishes) {
      // Court behind - increase threshold
      court.varietyThreshold = Math.min(100, court.varietyThreshold + 5);
    } else if (courtFinishes > avgFinishes + 1) {
      // Court ahead - decrease threshold
      court.varietyThreshold = Math.max(0, court.varietyThreshold - 5);
    } else {
      // Court balanced - drift toward 50
      if (court.varietyThreshold > 50) {
        court.varietyThreshold = Math.max(50, court.varietyThreshold - 2);
      } else if (court.varietyThreshold < 50) {
        court.varietyThreshold = Math.min(50, court.varietyThreshold + 2);
      }
    }
  });
}

/**
 * Update waitlist court tracking
 * Treats waitlist as a virtual court in the system
 */
export function updateWaitlistCourt(session: Session, waitlistSize: number): void {
  const state = session.courtVarietyState;
  const waitlistCourtCount = Math.floor(waitlistSize / 4);
  
  state.waitlistCourtCount = waitlistCourtCount;
  
  // Update waitlist court's finish count to reflect virtual courts
  const waitlistCourt = state.courtMixes.get(WAITLIST_COURT_NUMBER);
  if (waitlistCourt) {
    waitlistCourt.finishCount = waitlistCourtCount;
    state.totalCourtFinishes.set(WAITLIST_COURT_NUMBER, waitlistCourtCount);
  }
}

/**
 * Check if a court combination violates the HARD CAP
 * HARD CAP: Same courts cannot mix twice in a row
 * 
 * This means: If courts [1, 2, 0] mixed last round, they cannot mix again this round.
 * But [1, 3, 0] can mix (different combination).
 */
export function violatesHardCap(
  session: Session,
  courtsToMix: number[]
): boolean {
  if (courtsToMix.length === 0) {
    return false;
  }
  
  const state = session.courtVarietyState;
  
  // HARD CAP only applies after at least one round has been completed
  if (state.lastMixRound === 0) {
    return false; // No previous rounds, so no violation possible
  }
  
  // For every court in this mix, check if it mixed with the exact same set last round
  // If ALL courts mixed with the exact same combination, it violates HARD CAP
  return courtsToMix.every(courtNum => {
    const courtData = state.courtMixes.get(courtNum);
    if (!courtData) return false;
    
    // For each court, check if it has records of mixing with ALL other courts in proposed mix
    // This confirms the same combination was used last round
    return courtsToMix.every(other =>
      other === courtNum || courtData.lastMixedWith.has(other)
    );
  });
}

/**
 * Check if court should wait for diversity
 */
export function shouldCourtWaitForDiversity(
  session: Session,
  courtNumber: number,
  candidateCourts: number[]
): boolean {
  const state = session.courtVarietyState;
  const courtData = state.courtMixes.get(courtNumber);
  
  if (!courtData) return false;
  
  // HARD CAP CHECK: Must wait if all candidates mixed last round
  const allWerePrevious = candidateCourts.every(c => 
    courtData.lastMixedWith.has(c)
  );
  
  if (allWerePrevious) {
    return true;
  }
  
  // Additional check: high variety threshold
  if (courtData.varietyThreshold > 70) {
    return true;
  }
  
  return false;
}

/**
 * Get the best court mix combination
 * Respects HARD CAP: Never allows same courts to mix twice in a row
 */
export function getBestCourtMixCombination(
  session: Session,
  availableCourts: number[],
  numCourtsToMix: number = 2
): number[] | null {
  const state = session.courtVarietyState;
  
  if (availableCourts.length < numCourtsToMix) {
    return null;
  }
  
  // Score each court
  const scoredCourts = availableCourts.map(courtNum => {
    const courtData = state.courtMixes.get(courtNum);
    if (!courtData) return { court: courtNum, score: 0 };
    
    const finishCount = state.totalCourtFinishes.get(courtNum) || 0;
    const avgFinishes = Array.from(state.totalCourtFinishes.values())
      .reduce((a, b) => a + b, 0) / state.totalCourtFinishes.size;
    
    // Primary: courts with fewer finishes
    let score = -(finishCount - avgFinishes) * 100;
    
    // Secondary: variety threshold
    score += courtData.varietyThreshold;
    
    // Tertiary: not mixed recently
    score += courtData.lastMixedWith.size === 0 ? 50 : 0;
    
    return { court: courtNum, score };
  });
  
  scoredCourts.sort((a, b) => b.score - a.score);
  
  // Get top candidates
  const topCandidates = scoredCourts
    .slice(0, numCourtsToMix)
    .map(s => s.court)
    .sort();
  
  // Check HARD CAP
  if (violatesHardCap(session, topCandidates)) {
    // Find alternative by excluding one court that was mixed
    for (let i = 0; i < topCandidates.length; i++) {
      const alternative = [
        ...topCandidates.slice(0, i),
        ...topCandidates.slice(i + 1),
        scoredCourts[numCourtsToMix]?.court,
      ].filter(c => c !== undefined);
      
      if (alternative.length === numCourtsToMix && !violatesHardCap(session, alternative)) {
        return alternative.sort((a, b) => a - b);
      }
    }
    
    // No valid combination found
    return null;
  }
  
  return topCandidates;
}

/**
 * Determine if should wait for more courts
 */
export function shouldWaitForMoreCourts(
  session: Session,
  finishedCourts: number[]
): boolean {
  const state = session.courtVarietyState;
  
  if (finishedCourts.length === 0) return true;
  
  // Check finish count imbalance
  const finishCounts = Array.from(state.totalCourtFinishes.values());
  if (finishCounts.length > 0) {
    const maxFinishes = Math.max(...finishCounts);
    const minFinishes = Math.min(...finishCounts);
    
    if (maxFinishes - minFinishes > 2) {
      return true;
    }
  }
  
  // Single court with high threshold
  if (finishedCourts.length === 1) {
    const courtNum = finishedCourts[0];
    const courtData = state.courtMixes.get(courtNum);
    
    if (courtData && courtData.varietyThreshold > 75) {
      return true;
    }
  }
  
  return false;
}

/**
 * Get recommended number of courts to mix
 */
export function getRecommendedMixSize(
  session: Session,
  availableCourts: number[]
): number {
  if (availableCourts.length < 2) return availableCourts.length;
  if (availableCourts.length === 2) return 2;
  
  const state = session.courtVarietyState;
  const avgVariety = Array.from(state.courtMixes.values())
    .filter(c => c.courtNumber !== WAITLIST_COURT_NUMBER)
    .reduce((sum, c) => sum + c.varietyThreshold, 0) / 
    (state.courtMixes.size - 1);
  
  if (avgVariety > 70) {
    return Math.min(3, availableCourts.length);
  }
  
  return 2;
}

/**
 * Get summary of court variety state
 */
export function getCourtVarietySummary(session: Session): Record<string, any> {
  const state = session.courtVarietyState;
  
  const courtSummaries = Array.from(state.courtMixes.entries())
    .map(([num, data]) => ({
      court: num === WAITLIST_COURT_NUMBER ? 'WAITLIST' : `Court ${num}`,
      finishCount: data.finishCount,
      varietyThreshold: data.varietyThreshold,
      lastMixedWith: Array.from(data.lastMixedWith).map(c => 
        c === WAITLIST_COURT_NUMBER ? 'WAITLIST' : `Court ${c}`
      ),
    }));
  
  return {
    waitlistCourtCount: state.waitlistCourtCount,
    lastMixRound: state.lastMixRound,
    hardCapViolations: 0,
    courts: courtSummaries,
  };
}
