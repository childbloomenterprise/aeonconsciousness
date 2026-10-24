# AEON self-model ablation report

Pre-registration sha256: `ae676e9c9485361ee25e3b2549fb7c4539a75346e3bddd325e2b35fca18c3e11`  
Seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

| metric | intact | frozen_self_model | attention_disconnected | foreign_predictions | memory_loss | reduced_compute | simple_adaptive_controller |
|---|---|---|---|---|---|---|---|
| baseline | 0.91 | 0.92 | 0.92 | 0.24 | 0.93 | 0.94 | 0.92 |
| delay_recovery | 0.94 | 0.21 | 0.90 | 0.05 | 0.94 | 0.91 | 0.51 |
| catch_with_delay | 0.92 | 0.32 | 0.90 | 0.01 | 0.92 | 0.04 | 0.03 |
| vision_bias | 0.97 | 0.05 | 0.00 | 0.71 | 0.93 | 0.97 | 0.01 |
| vision_noise | 0.96 | 0.62 | 0.56 | 0.85 | 0.97 | 0.96 | 0.53 |
| recurrence_ticks | 29 | 24 | 27 | 25 | 28 | 15 | 276 |
| first_diag_ticks | 18 | 18 | 19 | 28 | 18 | 15 | 430 |
| tool_far | 0.75 | 0.01 | 0.90 | 0.31 | 0.46 | 0.91 | 0.04 |
| declined_unreachable | 0.90 | 0.90 | 0.90 | 0.28 | 0.90 | 0.90 | 0.00 |

## Pre-registered predictions

| id | condition | metric | expected | intact | observed | held |
|---|---|---|---|---|---|---|
| P1 | frozen_self_model | baseline | similar | 0.91 | 0.92 | yes |
| P2 | frozen_self_model | delay_recovery | lower | 0.94 | 0.21 | yes |
| P3 | frozen_self_model | catch_with_delay | lower | 0.92 | 0.32 | yes |
| P4 | frozen_self_model | tool_far | lower | 0.75 | 0.01 | yes |
| P5 | attention_disconnected | delay_recovery | similar | 0.94 | 0.90 | yes |
| P6 | attention_disconnected | vision_bias | lower | 0.97 | 0.00 | yes |
| P7 | attention_disconnected | vision_noise | lower | 0.96 | 0.56 | yes |
| P8 | foreign_predictions | baseline | lower | 0.91 | 0.24 | yes |
| P9 | memory_loss | delay_recovery | similar | 0.94 | 0.94 | yes |
| P10 | memory_loss | catch_with_delay | similar | 0.92 | 0.92 | yes |
| P11 | memory_loss | recurrence_ticks | higher | 29 | 28 | **no** |
| P12 | reduced_compute | catch_with_delay | lower | 0.92 | 0.04 | yes |
| P13 | reduced_compute | delay_recovery | similar | 0.94 | 0.91 | yes |
| P14 | simple_adaptive_controller | catch_with_delay | lower | 0.92 | 0.03 | yes |
| P15 | simple_adaptive_controller | vision_bias | lower | 0.97 | 0.01 | yes |
| P16 | simple_adaptive_controller | tool_far | lower | 0.75 | 0.04 | yes |

**15/16 predictions held.**

Numbers are internal estimates and behavioural measures. They test the causal role of a self-model; they do not establish subjective experience.
