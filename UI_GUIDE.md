# UI Guide - Pickleball Session Manager

## Court Display Layout

### New Horizontal Layout (v2.1)

```
┌─────────────────────────────────────────────────────────┐
│               Court 1    [In Progress]                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  TEAM 1    │    │   CONTROLS   │    │  TEAM 2    │ │
│  │            │    │              │    │            │ │
│  │  Alice     │    │  [11] vs [9] │    │  Carol     │ │
│  │  Bob       │    │              │    │  Dave      │ │
│  │            │    │  [Complete]  │    │            │ │
│  │            │    │  [Forfeit]   │    │            │ │
│  └────────────┘    └──────────────┘    └────────────┘ │
│   (Blue border)                        (Purple border) │
└─────────────────────────────────────────────────────────┘
```

### Benefits of New Layout:
- ✅ Left vs Right is more intuitive than Top vs Bottom
- ✅ Easier to see which team is which
- ✅ Controls centered between teams
- ✅ Color-coded borders (blue for Team 1, purple for Team 2)
- ✅ Better use of screen space

### Old Layout (v2.0)
```
┌────────────────────────┐
│ Court 1 [In Progress]  │
├────────────────────────┤
│ Team 1:                │
│ Alice, Bob             │
│                        │
│ Team 2:                │
│ Carol, Dave            │
│                        │
│ [11] vs [9]            │
│ [Complete] [Forfeit]   │
└────────────────────────┘
```

## Match History Display

### History Card Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ Court 2                                        [Completed] ✓     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │  Alice & Bob    │  │  [11] - [7]   │  │  Carol & Dave    │ │
│  │   (Winner) ✓    │  │  [Save]       │  │   (Loser)        │ │
│  └─────────────────┘  └───────────────┘  └──────────────────┘ │
│   Green background      Edit scores       Red background       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Features:
- 🏆 Winners highlighted in green with border
- ❌ Losers shown in red with border
- ✏️ Editable score inputs
- 💾 Save button to update scores
- 🔄 Stats recalculated automatically on save

### Forfeited Matches Display

```
┌─────────────────────────────────────────────────────────────────┐
│ Court 1                                        [Forfeited] ⚠     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Alice & Bob            vs           Carol & Dave               │
│                                                                  │
│  (No scores recorded - no winner/loser highlighting)            │
└─────────────────────────────────────────────────────────────────┘
```

## Session Controls Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Session Controls                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Active Players:                                              │
│ [____________] [Add Player]                                  │
│                                                              │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ Alice       │ │ Bob         │ │ Carol       │            │
│ │ [Remove]    │ │ [Remove]    │ │ [Remove]    │            │
│ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                              │
│ ┌───────────────────────────┐ (Inactive - grayed out)       │
│ │ Dave (Inactive)           │                                │
│ │ [Reactivate]              │                                │
│ └───────────────────────────┘                                │
│                                                              │
│ [Show Statistics] [Show History] [End Session]              │
└─────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Court Display
- **Team 1 Border**: Blue (#667eea)
- **Team 2 Border**: Purple (#764ba2)
- **Background**: Light gray (#f8f9fa)

### Match Status Badges
- **Waiting**: Yellow (#ffc107) with black text
- **In Progress**: Green (#28a745) with white text
- **Completed**: Gray (#6c757d) with white text
- **Forfeited**: Red (#dc3545) with white text

### Match History
- **Winner Box**: Light green (#d4edda) with green border (#28a745)
- **Loser Box**: Light red (#f8d7da) with red border (#dc3545)
- **Neutral Box**: Light gray (#f8f9fa)

### Buttons
- **Primary**: Purple gradient (#667eea to #764ba2)
- **Success**: Green (#28a745)
- **Danger**: Red (#dc3545)
- **Secondary**: Gray (#6c757d)

## Responsive Behavior

### Desktop (> 1200px)
- Courts displayed in grid (2-3 columns)
- Full horizontal layout for each court
- History cards full width

### Tablet (768px - 1200px)
- Courts displayed in grid (1-2 columns)
- Maintained horizontal layout
- History cards full width

### Mobile (< 768px)
- Courts stacked vertically
- Teams may stack on very small screens
- History adapts to vertical layout

## Interaction Flow

### Completing a Match
1. User sees court with in-progress match
2. Teams displayed on left and right
3. Score inputs in center
4. Enters scores (e.g., 11 - 9)
5. Clicks "Complete"
6. Match disappears from active courts
7. New match automatically appears (if players waiting)
8. Completed match appears in history

### Editing a Score
1. Click "Show History"
2. Find the match to edit
3. Change score values directly in the inputs
4. Click "Save"
5. Alert confirms update
6. Statistics automatically recalculated
7. Winner/loser highlighting updates

### Forfeiting a Match
1. Match in progress
2. Click "Forfeit" button
3. Confirmation dialog
4. Match removed from active courts
5. Court freed immediately
6. New match created if players available
7. Forfeited match appears in history (no scores)

## Navigation Flow

```
Setup Screen
    ↓
[Start Session]
    ↓
Session Controls (always visible)
    ├─ Active Players List
    ├─ Add Player Input
    └─ Control Buttons
    
Active Courts (always visible when matches exist)
    ├─ Court 1 (Horizontal Layout)
    ├─ Court 2 (Horizontal Layout)
    └─ Waiting Players Area
    
Statistics (toggle)
    └─ Player Cards

Match History (toggle)
    └─ Historical Matches (most recent first)
```

## Best Practices for Display

### Court Display
- Keep team names short (truncate if needed)
- Score inputs use large, bold font
- Clear visual separation between teams
- Status badge always visible

### Match History
- Show 10-20 most recent matches by default
- Scroll for older matches
- Maintain chronological order (newest first)
- Clear winner/loser indication

### Player Management
- Active players at top
- Inactive players at bottom (grayed)
- Easy access to add/remove buttons
- Visual feedback on status changes

## Accessibility Features

- ✅ High contrast text
- ✅ Clear visual hierarchy
- ✅ Large clickable targets (>44px)
- ✅ Color + text for status (not color alone)
- ✅ Keyboard navigation support
- ✅ Screen reader friendly labels

## Performance Notes

- History renders on demand (toggle)
- Only active matches rendered in real-time
- Efficient DOM updates
- Smooth transitions and animations
