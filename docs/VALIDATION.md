# Validation

Every engine model is checked against an independent reference. The checks run on every pull
request (`engine/tests`); this page lists them. Acceptance criterion (ROADMAP M3):
|x_new − x_ref| / |x_ref| < ε, with ε per quantity below.

Status: model-level validation done for the demo units. Process-level validation (M3): the HDA
plant against the maintainer's CHEMCAD case, and two published CHEMCAD stream tables (cumene,
DME) — all below.

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
| Shortcut column options | Condenser temperature (two-phase distillate, component balances), pressure drop (bottoms at P + ΔP), absent components | balances, P | 1e-9 rel. | `test_column_options.py` |
| Rigorous column | MESH equations on every stage; FUG design | residuals; recovery, x_D, Q_c | 1e-6; 0.03, 0.02, 5 % | `test_distillation_column.py` |
| CSTR / PFR | First-order X = kτ/(1+kτ), X = 1 − e^(−kτ); second-order CSTR | conversion | 1e-6 rel. | `test_kinetic_reactors.py` |
| Adiabatic PFR | Same outlet T as an adiabatic conversion reactor at equal conversion | T | 1e-3 K | `test_adiabatic_pfr…` |
| Equilibrium reactor | K condition, element balances, Le Chatelier | composition | 1e-7 rel. | `test_equilibrium_reactor.py` |
| Liquid equilibrium, ideal A ⇌ B | x_B/x_A = K_a; formation route K_a = K_ig·Psat_A/Psat_B | ratio | 1e-6 rel. | `test_liquid_equilibrium.py::test_ideal_isomerisation…` |
| MTBE K_a(T) from formation data | ln K = 4703/T − 10.3 (Izquierdo et al., via Badia et al. 2016); ΔrH° = −37 ± 10 kJ/mol | ln K, ΔrH° | 0.45, 10 kJ/mol | `test_mtbe_k_from_formation_data_vs_literature` |
| MTBE, NRTL liquid | Π(x γ)^ν = K_a with γ from the model | K_a | 1e-6 rel. | `test_nrtl_outlet_satisfies_activity_mass_action` |
| Recycle loops | Analytic R = rF/(1 − r); once-through duties | flows, duties | 1e-6 rel. | `test_recycle.py` |

## Literature cases (published CHEMCAD stream tables)

### Cumene, Unit 800 — Turton (WVU), SRK

Source: R. Turton, *Cumene Production – Change in Reactor Conditions*, Appendix 1 (Table 1 and
equipment summary), <https://richardturton.faculty.wvu.edu/files/d/3bcf319c-2670-4fae-926f-04045aa5f217/cumene2.pdf>.
Example `cumene-unit-800-validation`: Stream 6 → E-801 → H-801 → R-801 (conversions from the
Stream 7 → 8 extents) → E-802 → V-802. Test: `test_literature_cases.py`.

| Quantity | Published | Engine (SRK) | Deviation | ε |
|---|---|---|---|---|
| E-801 duty | 12,800 MJ/h | 12,929 MJ/h | +1.0 % | 4 % |
| H-801 duty | 6,334 MJ/h | 6,494 MJ/h | +2.5 % | 4 % |
| R-801 heat removal | 9,840 MJ/h | 9,722 MJ/h | −1.2 % | 4 % |
| E-802 duty | 16,257 MJ/h | 16,737 MJ/h | +3.0 % | 4 % |
| V-802 vapour (Stream 9) | 19.89 kmol/h | 20.01 kmol/h | +0.6 % | 3 % |
| Stream 9 propylene / propane / benzene / cumene | 5.97 / 5.27 / 7.88 / 0.77 | 5.99 / 5.27 / 7.93 / 0.82 | ≤ 0.05 kmol/h | 0.1 kmol/h |
| Stream 10 benzene / cumene / p-DIPB | 101.08 / 93.62 / 2.79 | 101.10 / 93.57 / 2.79 | ≤ 0.1 % | 0.5 % |

### Dimethyl ether, Unit 200 — Turton (WVU)

Source: R. Turton, *Production of Dimethyl Ether*, stream tables (original: NRTL K-values, SRK
enthalpies), <https://richardturton.faculty.wvu.edu/files/d/7cd9840b-ef1f-4995-9ebe-7d654abf91ea/dimethyl_ether.pdf>.
Example `dme-unit-200-validation` (NRTL). Test: `test_literature_cases.py`.

| Quantity | Published | Engine | Deviation | ε |
|---|---|---|---|---|
| R-101 adiabatic outlet T (80 % conversion) | 365.65 °C | 368.26 °C (PR) | +2.6 K | 3 K |
| Same with NRTL (ideal-gas vapour enthalpy) | 365.65 °C | 376.0 °C | +10.4 K | not tested — use an EOS for gas-phase reactors |
| Stream 11 (let-down to 6.91 atm) | 138.82 °C, VF 0.046 | 138.93 °C, VF 0.025 | +0.1 K | 0.3 K, 0.03 |
| Stream 14 (let-down to 1.09 atm) | 80.93 °C, VF 0.14 | 80.66 °C, VF 0.10 | −0.3 K | 0.5 K, 0.05 |
| Stream 7 VF (135.19 °C, 14.9 atm) | 0.50 | 0.41 | −0.09 | **known gap** |
| Stream 8 (let-down to 10.26 atm) | 125.56 °C, VF 0.53 | 121.3 °C, VF 0.44 | −4.2 K | **known gap** |

Known gap: the ChemSep NRTL table shipped with `thermo` has no DME–methanol and DME–water
pairs, so the engine treats them as ideal (warning `missing_binary_parameter`). Streams 7–8
contain 39 % DME, so their phase split is off; enter literature NRTL parameters for these pairs
on the Thermodynamics page to close it.

### HDA plant — maintainer's CHEMCAD 8.1 case (SRK)

Source: stream table "CHEMCAD-SON (1)" of the maintainer's KMM4125 design project (CHEMCAD 8.1.0,
exported 2026-11-26), stored as `engine/tests/data/hda_chemcad_case.json`. Example
`hda-chemcad-validation` rebuilds the flowsheet with CHEMCAD's stream and equipment numbers:
feed compressor and pump, two mixers, fired heater, one isothermal reactor at 620 °C with two
reactions (75 % toluene conversion, then 2 % of the benzene to biphenyl — CHEMCAD models this as
two stoichiometric reactors in series, units 6 and 7), cooler, flash at 38 °C / 31.8 bar, 15 % purge,
recycle compressor, let-down valve, flash at 2 bar, benzene column (top 2.0 bar, bottom 2.1 bar,
condenser at 50 °C with a drum for the off-gas, stream 25) and toluene column, recycle pump.

Specifications come from the stream table (T, P, purge fraction, key recoveries) and the
maintainer's screen recording of the CHEMCAD dialogs (reactor conversions and stoichiometry,
efficiencies 0.75, benzene column: partial condenser, 25 stages, feed on stage 12, top 2 bar,
column ΔP 0.1 bar). Columns are FUG shortcuts,
so CHEMCAD's column duties (not in the table) are not compared. Duties below are CHEMCAD stream
enthalpy differences (heat-of-formation basis, like the engine's reactor balance). Property
method: SRK. With PR the engine gives 0.6 % more recycle gas, 10 % more benzene in it and 25 %
less methane dissolved in the 38 °C / 31.8 bar liquid, so the CHEMCAD case was most likely run
with SRK. Both recycles converge
(Wegstein, from rounded start estimates). Test: `test_hda_chemcad.py`.

| Quantity | CHEMCAD | Engine | Deviation | ε |
|---|---|---|---|---|
| Reactor feed, Stream 6 | 421.70 kmol/h, 89.60 °C, VF 0.9181 | 421.38 kmol/h, 89.49 °C, VF 0.9181 | −0.08 %, −0.11 K | 0.5 %, 0.3 K, 0.003 |
| Gas recycle, Stream 15 | 324.06 kmol/h | 323.75 kmol/h | −0.10 % | 0.5 % |
| Toluene recycle, Stream 24 | 9.480 kmol/h, 138.29 °C | 9.472 kmol/h, 138.26 °C | −0.08 %, −0.03 K | 0.5 %, 0.2 K |
| Purge (fuel gas), Stream 14 | 57.19 kmol/h | 57.13 kmol/h | −0.10 % | 0.5 % |
| HP flash liquid, Stream 11 | 40.446 kmol/h | 40.494 kmol/h | +0.12 % | 0.5 % |
| Let-down to 2 bar, Stream 16 | 37.43 °C, VF 0.0512 | 37.40 °C, VF 0.0531 | −0.03 K, +0.002 | 0.2 K, 0.003 |
| Benzene product, Stream 20 | 28.493 kmol/h, x_B 0.9942 | 28.471 kmol/h, x_B 0.9942 | −0.08 % | 0.5 %, 5e-4 |
| Biphenyl, Stream 22 | 0.320 kmol/h, 290.79 °C | 0.321 kmol/h, 290.78 °C | +0.17 % | 0.5 %, 0.2 K |
| Column 15 bottoms, Stream 21 | 139.95 °C | 139.90 °C | −0.05 K | 0.2 K |
| Column 16 distillate, Stream 23 | 136.54 °C | 136.50 °C | −0.04 K | 0.2 K |
| H2 compressor outlet, Stream 2 | 654.01 °C | 652.71 °C | −1.3 K | 2 K |
| Fired heater E-5 duty | 3818 kW | 3830 kW | +0.31 % | 1 % |
| Reactor R-6 heat removed (CHEMCAD units 6 + 7) | 407.4 kW | 404.5 kW | −0.71 % | 1 % |
| Cooler E-8 duty | 4060 kW | 4070 kW | +0.26 % | 1 % |
| H2 compressor K-2 power (dialog: 419.638 hp) | 312.9 kW | 312.6 kW | −0.09 % | 1 % |
| Recycle compressor K-11 power (dialog: 2.59608 hp) | 1.936 kW | 1.933 kW | −0.17 % | 1 % |
| Pumps P-1 / P-17 power | 3.64 / 1.29 kW | 3.64 / 1.29 kW | +0.15 / −0.20 % | 1 % |
| Light ends, Stream 17 | 2.077 kmol/h | 2.158 kmol/h | +3.9 % | 6 % |
| Column off-gas, Stream 25 | 0.076 kmol/h | 0.072 kmol/h | −5.5 % | 8 % |

Streams 17 and 25 carry only the H2 and CH4 dissolved in the liquid (2 and 0.08 kmol/h); they
depend on gas solubilities, i.e. on the SRK binary parameters, which CHEMCAD and the ChemSep
table shipped with `thermo` do not share (missing pairs are reported). Their deviations are
recorded rather than hidden by loose tolerances on the main streams.

### HDA plant template — sanity against Turton et al., ch. 1

Example `hda-benzene-plant-template` (PR; two recycles, adiabatic R-101 at 75 % per pass, FUG
column). Its specifications are illustrative, so this is a plausibility check, not a validation;
the validated HDA case is `hda-chemcad-validation` (above). Turton values as quoted from
Table 1.5 in course material. Tested: atom balances close (1e-5) and the per-pass conversion.

| Quantity | Turton (Table 1.5) | Template |
|---|---|---|
| Reactor inlet toluene (Stream 6) | 144.0 kmol/h | 143.5 kmol/h |
| Reactor outlet T (Stream 9) | 654 °C | 659.8 °C |
| Reactor outlet benzene / toluene | 116.0 / 36.0 kmol/h | 116.9 / 35.9 kmol/h |
| Fuel gas | 304 kmol/h | 307 kmol/h |

## Browser engine

All examples are solved in Pyodide (`web/src/engine/engine.spike.test.ts`) and give the same
numbers as native CPython (flash-drum S2 x_benzene 0.6211 in both).

## Next (M3)

1. Done: HDA vs. the maintainer's CHEMCAD case (`hda-chemcad-validation`, above). Open: the benzene column's *Specifications* tab (reflux or distillate spec) and the toluene column's settings, to compare rigorous columns and their duties (QUESTIONS Q9).
2. Done: cumene (Unit 800) and DME (Unit 200) from Turton's published CHEMCAD tables (above).
3. Record agreed ε values here and keep them as test tolerances.
