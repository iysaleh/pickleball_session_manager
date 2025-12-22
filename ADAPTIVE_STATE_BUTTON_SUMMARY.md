## Adaptive Slider State Button Implementation

### Summary of Changes

I've successfully implemented the requested state button functionality for the adaptive constraints slider. The user can now easily toggle between three states: **Disabled**, **Auto**, and **Manual**, with **Auto** as the default.

### New Features

1. **State Toggle Button**: 
   - Added below the adaptive slider
   - Cycles through: Disabled → Auto → Manual → Disabled
   - **Auto is the default state** for new sessions
   - Clear visual indication of current mode

2. **Three-State System**:
   - **Disabled State**: Adaptive constraints completely off, slider disabled, shows "Disabled"
   - **Auto State**: Automatic progression (Early→Mid→Late), slider disabled, shows "Auto: Phase (weight)"
   - **Manual State**: User controls balance weighting, slider enabled for positions 2-5 (Low to Max)

### 3. **Slider Behavior**:
   - Only enabled in Manual mode for user interaction
   - **Automatically moves in Auto mode** to show current phase (position 1→3→4)
   - Range: 1-5 (Early 1.0x, Mid 3.0x, Late 5.0x, Manual 8.0x)
   - Labels: "LOW" to "MAX"
   - Visually disabled when in Disabled or Auto states (but still moves in Auto)

### Implementation Details

#### GUI Components (`python/gui.py`):

- **State Button**: `self.adaptive_state_button`
  - Cycles through three states: Disabled → Auto → Manual → Disabled
  - Defaults to "Auto" text on initialization
  - Updates both button text and system state

- **Updated Slider Logic**: 
  - Slider only responds to input in Manual mode
  - Automatic range adjustment (min=2 in Manual, min=0 in other modes)
  - Clear visual disabled state when not in Manual mode

#### State Management:

- **Disabled**: `session.adaptive_constraints_disabled = True, session.adaptive_balance_weight = None`
- **Auto** (Default): `session.adaptive_constraints_disabled = False, session.adaptive_balance_weight = None`
- **Manual**: `session.adaptive_constraints_disabled = False, session.adaptive_balance_weight = float (2.0-8.0)`

### Testing

Updated comprehensive test suite (`test_adaptive_state_button.py`) that validates:

✅ Automatic slider movement in Auto mode (visual feedback)
✅ Three-state transition logic (Disabled → Auto → Manual → Disabled)
✅ Auto as default state with automatic progression
✅ Slider behavior in each state (disabled vs enabled)
✅ Weight mapping (2.0x, 3.0x, 5.0x, 8.0x)
✅ Auto state shows current phase (Early/Mid/Late)
✅ Button click cycle simulation
✅ Integration with existing competitive variety system
✅ Backwards compatibility

### User Experience

**Before**: Complex slider with positions that were hard to understand
**After**: Clear state button + slider for fine-tuning when needed

This provides the requested functionality with clear separation:

1. **Auto (Default)**: Adaptive constraints automatically adjust based on session progression (Early 1.0x → Mid 3.0x → Late 5.0x)
2. **Manual**: User controls balance weighting via slider (2.0x to 8.0x)
3. **Disabled**: Adaptive constraints completely turned off

The variety slider behavior remains unchanged as requested - adaptive constraints don't affect user variety preferences, only the balance weighting in the algorithm.

### Key Benefits

- **Easy toggle**: Single button click to cycle through modes
- **Auto default**: Most users can ignore the feature and get automatic optimization
- **Expert control**: Advanced users can manually tune balance weighting
- **Clear feedback**: Status shows exactly what mode and weight is active