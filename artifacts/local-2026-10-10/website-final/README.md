# Portable Offline Tip Calculator

A simple, lightweight, and fully offline tip calculator built with HTML, CSS, and JavaScript in a single file (`index.html`).

## Features
- **Light Background with Purple Accent**: Clean, modern interface designed with accessibility and readable labels in mind.
- **Keyboard Focus & Accessible Controls**: High contrast focus indicators and minimum 44px button sizing for seamless interaction.
- **Responsive Layout**: Adapts smoothly to both desktop and mobile screens without horizontal or vertical overflow.
- **Robust Validation**: Rejects negative numbers with a descriptive error message ("Please enter valid non-negative numbers for bill amount and tip percentage.") and safely resets totals to zero.

## Verified Test Cases
1. **Normal Input (100 / 15)**:
   - Bill Amount: 100
   - Tip Percentage: 15
   - Result: Tip Amount **15.00**, Total Amount **115.00** (Passed)
2. **Zero Input (0 / 20)**:
   - Bill Amount: 0
   - Tip Percentage: 20
   - Result: Tip Amount **0.00**, Total Amount **0.00** (Passed)
3. **Negative Input (-1 / 15)**:
   - Bill Amount: -1
   - Tip Percentage: 15
   - Result: Triggers error message "Please enter valid non-negative numbers for bill amount and tip percentage." with zero totals (Passed)

## Opening Instructions
Simply open `index.html` in any modern web browser. No server, CDN, or internet connection required.
## Independent assisted finish
Original worker output preserved separately. This copy adds Enter-key calculation for either input; original worker did not implement that enhancement. Independent downloaded-original calculation checks passed; corrected copy receives separate desktop/mobile checks and hashes. No original job status or audit was edited.
