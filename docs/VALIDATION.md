# Validation

Every engine model is checked against an independent reference. The checks run on every pull
request (`engine/tests`); this page lists them. Acceptance criterion (ROADMAP M3):
|x_new − x_ref| / |x_ref| < ε, with ε per quantity below.

Status: model-level validation done for the demo units. **Process-level validation (M3) is open:**
the HDA process against the maintainer's CHEMCAD case, plus two or three literature processes
(methanol, cumene) — see "Next".

## Thermodynamics

| Case | Reference | Quantity | ε | Test |
|---|---|---|---|---|
| Benzene–toluene flash, Ideal | Raoult + Antoine (Felder & Rousseau, Table B.4), Rachford–Rice | vapour fraction, y | 0.01, 0.003 abs. | `test_reference_adapter.py::test_ideal_flash_matches_raoult_hand_calculation` |
| Pure benzene, toluene, PR and SRK | NIST WebBook normal boiling points | T_b | 1.5 K | `test_pure_component_boiling_point` |
| Methanol–water, NRTL, 1 atm | Experimental VLE (Perry's Handbook) at x = 0.1, 0.3, 0.5, 0.8 | T, y | 0.7 K, 0.02 | `test_nrtl.py::test_methanol_water_matches_experiment` |
| Ethanol–water, NRTL | Azeotrope 78.15 °C at x = 0.894 (CRC) | T, direction of y − x | 0.6 K | `test_ethanol_water_minimum_boiling_azeotrope` |
| Methanol–water, UNIQUAC, 1 atm | Same data; engine 87.49 / 77.94 / 73.01 / 67.60 °C vs 87.7 / 78.0 / 73.1 / 67.6 °C | T, y | 0.7 K, 0.02 | `test_uniquac.py::test_methanol_water_uniquac_matches_experiment` |
| Ethanol–water, UNIQUAC | Azeotrope 78.15 °C at x = 0.894 (CRC); engine 78.82 °C | T | 0.8 K | `test_ethanol_water_azeotrope_uniquac` |
| Water–gas shift K(T) | Moe (1962) correlation, 600–800 K | K | 6 % | `test_equilibrium_reactor.py` |

## Units

| Unit | Reference | Quantity | ε | Test |
|---|---|---|---|---|
| Pump | ṁΔP/(ρη), ρ(water, 298 K) from NIST | power | 2 % | `test_units_t09.py::test_pump_power…` |
| Compressor | Ideal-gas isentropic relation, N2, γ = 1.4 | outlet T, power | 2 K, 2 % | `test_compressor_matches…` |
| Heat exchanger | Duty from both sides; LMTD and UA definitions | duty, LMTD | 1e-6 rel. | `test_heat_exchanger…` |
| HX zones, isothermal condensing side | Classic LMTD is exact for a constant hot temperature | UA | 0.5 % | `test_heat_exchanger_zones.py::test_isothermal_condensing_side_matches_lmtd` |
| HX zones, desuperheat–condense–subcool | Grid independence (1 zone + phase boundaries vs 100 zones) | UA | 0.2 % | `test_phase_change_zoned_ua_is_grid_independent…` |
| HX internal pinch | Hand balance at the steam dew point, ideal-gas cp of steam and N2 (NIST Shomate) | minimum approach | 0.3 K | `test_internal_pinch_at_dew_point_matches_hand_balance` |
| HX rating with phase change | Rated UA reproduces the design duty | duty | 1e-6 rel. | `test_rating_reproduces_phase_change_design` |
| Shell-and-tube, tube side | Hand calculation, Dittus–Boelter + OU friction/return-loss model, NIST water at 300 K | v, Re, h_t, ΔP_t | 0.5 %, 1 %, 3 %, 1 % | `test_shell_and_tube.py::test_tube_side…` |
| Shell-and-tube, shell side | Hand calculation, Kern (1950) D_e, h_s and ΔP_s, NIST water at 300 K | v, Re, h_s, ΔP_s | 0.5 %, 1 %, 3 %, 1 % | `test_shell_side…` |
| F correction (1–2N) | Bowman et al. (1940): R = 1, P = 0.5 → 0.802; reciprocity F(R,P) = F(1/R, PR) | F | 5e-4 | `test_f_correction_reference_values` |
| Geometry rating | U·A·F equals the zoned UA; design check at the rated outlet gives zero over-design | UA, over-design | 1e-5 | `test_rating_from_geometry…` |
| Conversion reactor | ΔHr° of toluene HDA from formation enthalpies (≈ −42 kJ/mol) | duty | 2 % | `test_conversion_reactor…` |
| Shortcut column | Closed-form binary Fenske and Underwood | N_min, R_min | 1e-9, 1e-4 rel. | `test_shortcut_column_binary…` |
| Rigorous column | MESH equations on every stage; FUG design | residuals; recovery, x_D, Q_c | 1e-6; 0.03, 0.02, 5 % | `test_distillation_column.py` |
| CSTR / PFR | First-order X = kτ/(1+kτ), X = 1 − e^(−kτ); second-order CSTR | conversion | 1e-6 rel. | `test_kinetic_reactors.py` |
| Adiabatic PFR | Same outlet T as an adiabatic conversion reactor at equal conversion | T | 1e-3 K | `test_adiabatic_pfr…` |
| Equilibrium reactor | K condition, element balances, Le Chatelier | composition | 1e-7 rel. | `test_equilibrium_reactor.py` |
| Liquid equilibrium, ideal A ⇌ B | x_B/x_A = K_a; formation route K_a = K_ig·Psat_A/Psat_B | ratio | 1e-6 rel. | `test_liquid_equilibrium.py::test_ideal_isomerisation…` |
| MTBE K_a(T) from formation data | ln K = 4703/T − 10.3 (Izquierdo et al., via Badia et al. 2016); ΔrH° = −37 ± 10 kJ/mol | ln K, ΔrH° | 0.45, 10 kJ/mol | `test_mtbe_k_from_formation_data_vs_literature` |
| MTBE, NRTL liquid | Π(x γ)^ν = K_a with γ from the model | K_a | 1e-6 rel. | `test_nrtl_outlet_satisfies_activity_mass_action` |
| Recycle loops | Analytic R = rF/(1 − r); once-through duties | flows, duties | 1e-6 rel. | `test_recycle.py` |

## Browser engine

All examples are solved in Pyodide (`web/src/engine/engine.spike.test.ts`) and give the same
numbers as native CPython (flash-drum S2 x_benzene 0.6211 in both).

## Next (M3)

1. **HDA vs. CHEMCAD.** Maintainer: export the CHEMCAD stream table (T, P, flows, compositions) of the HDA design-course case. We rebuild the case as `examples/hda-validated.opd.json` and add a test with ε per quantity.
2. **Methanol synthesis** and **cumene** from published design cases (literature tables with stream data).
3. Record agreed ε values here and keep them as test tolerances.
