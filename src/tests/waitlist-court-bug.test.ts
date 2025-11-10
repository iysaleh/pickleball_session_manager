import { describe, it, expect } from 'vitest';
import { initializeCourtVarietyState, recordCourtMix, violatesHardCap } from '../../src/court-variety';
import type { Session } from '../../src/types';

describe('Waitlist Court HARD CAP Fix - 11 Players, 3 Courts', () => {
  
  it('should NOT block court mixing when waitlist is involved', () => {
    // Create a mock session with court variety state
    const session = {
      courtVarietyState: initializeCourtVarietyState(4),
    } as Session;
    
    // Simulate first round: courts [1, 0] mix (court 1 with waitlist)
    const firstMixOK = recordCourtMix(session, [1, 0]);
    expect(firstMixOK).toBe(true);
    
    // Simulate second round: courts [1, 0] try to mix again
    // This should be ALLOWED because the waitlist should not trigger HARD CAP
    const secondMixOK = recordCourtMix(session, [1, 0]);
    expect(secondMixOK).toBe(true); // Should NOT violate HARD CAP
  });
  
  it('should block two physical courts from mixing twice in a row', () => {
    const session = {
      courtVarietyState: initializeCourtVarietyState(4),
    } as Session;
    
    // Simulate first round: courts [1, 2] mix (two physical courts)
    const firstMixOK = recordCourtMix(session, [1, 2]);
    expect(firstMixOK).toBe(true);
    
    // Simulate second round: courts [1, 2] try to mix again
    // This should be BLOCKED by HARD CAP
    const secondMixOK = recordCourtMix(session, [1, 2]);
    expect(secondMixOK).toBe(false); // Should violate HARD CAP
  });
  
  it('should allow court 1 to mix with different physical courts even if it used waitlist before', () => {
    const session = {
      courtVarietyState: initializeCourtVarietyState(4),
    } as Session;
    
    // Round 1: court [1, 0] (court 1 with waitlist)
    const firstOK = recordCourtMix(session, [1, 0]);
    expect(firstOK).toBe(true);
    
    // Round 2: courts [1, 2] (court 1 with court 2)
    // This should be allowed - different physical court combination
    const secondOK = recordCourtMix(session, [1, 2]);
    expect(secondOK).toBe(true);
  });
  
  it('should allow court 1 with waitlist, then court 2 with waitlist', () => {
    const session = {
      courtVarietyState: initializeCourtVarietyState(4),
    } as Session;
    
    // Round 1: courts [1, 0] mix
    const firstOK = recordCourtMix(session, [1, 0]);
    expect(firstOK).toBe(true);
    
    // Round 2: courts [2, 0] mix (different physical court with waitlist)
    const secondOK = recordCourtMix(session, [2, 0]);
    expect(secondOK).toBe(true);
    
    // Round 3: courts [1, 0] can mix again
    const thirdOK = recordCourtMix(session, [1, 0]);
    expect(thirdOK).toBe(true);
  });
  
  it('violatesHardCap should return false when only one physical court involved', () => {
    const session = {
      courtVarietyState: initializeCourtVarietyState(4),
    } as Session;
    
    // Setup: record court 1 with waitlist
    recordCourtMix(session, [1, 0]);
    
    // Check if [1, 0] violates HARD CAP
    expect(violatesHardCap(session, [1, 0])).toBe(false); // Single physical court - no HARD CAP
  });
});
