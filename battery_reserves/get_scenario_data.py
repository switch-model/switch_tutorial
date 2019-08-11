#!/usr/bin/env python

from __future__ import print_function
import sys, os, argparse
from textwrap import dedent

import switch_model.hawaii.scenario_data as scenario_data

###########################
# Scenario Definitions

# definitions of standard scenarios (may also specify inputs_subdir to read in alternative data)
# TODO: find a way to define the base scenario here, then apply the others as changes to it
# Maybe allow each to start with --inherit-scenario <parent>? (to one level)
# (--scenario does this already)

scenario_columns = (
    'scenario_name',      'dr_share', 'ev_timing', 'ls_bat_reserve_type', 'dr_res_types'
)
scenarios = [
    # name, dr share, type of reserves from load-shifting batteries, reserves from dr
    ('battery_bulk',             0.0, 'bau',     'none',        'none'),
    ('battery_bulk_and_conting', 0.0, 'bau',     'contingency', 'none'),
    ('battery_bulk_and_reg',     0.0, 'bau',     'regulation',  'none'),
    ('dr_bulk',                  0.1, 'optimal', 'regulation',  'none'),
    ('dr_bulk_and_reserves',     0.1, 'optimal', 'regulation',  'regulation contingency'),
]
scenario_dict_list = [dict(zip(scenario_columns, scen)) for scen in scenarios]

#import pdb; pdb.set_trace()

scenario_list = [
    '--scenario-name {scenario_name}_long --outputs-dir outputs/{scenario_name} '
    '--inputs-dir inputs/{ls_bat_reserve_type} '
    '--demand-response-share {dr_share} --ev-timing {ev_timing} '
    '--demand-response-reserve-types {dr_res_types} --ev-reserve-types {dr_res_types}'
    .format(**dct)
    for dct in scenario_dict_list
]

print("Writing scenarios.txt")
with open('scenarios.txt', 'w') as f:
    f.writelines(s + '\n' for s in scenario_list)

parser = argparse.ArgumentParser()
parser.add_argument('--skip-cf', action='store_true', default=False,
    help='Skip writing variable capacity factors file (for faster execution)')

cmd_line_args = parser.parse_args()

# particular settings chosen for this case
# (these will be passed as arguments when the queries are run)
args = dict(
    # directory to store data in
    inputs_dir = 'inputs',
    # skip writing capacity factors file if specified (for speed)
    skip_cf = cmd_line_args.skip_cf,
    # use heat rate curves for all thermal plants
    use_incremental_heat_rates=True,
    # could be 'tiny', 'rps', 'rps_mini' or possibly '2007', '2016test', 'rps_test_45', or 'main'
    # '2020_2025' is two 5-year periods, with 24 days per period, starting in 2020 and 2025
    # "2020_2045_23_2_2" is 5 5-year periods, 6 days per period before 2045, 12 days per period in 2045, 12 h/day
    # time_sample = "2020_2045_23_2_2", # 6 mo/year before 2045
    time_sample = "2020_2045_23_2",  # 12 mo/year all the way through
    # subset of load zones to model
    load_zones = ('Oahu',),
    # "hist"=pseudo-historical, "med"="Moved by Passion", "flat"=2015 levels, "PSIP_2016_04"=PSIP 4/16
    load_scen_id = "PSIP_2016_12",
    # "PSIP_2016_12"=PSIP 12/16 or "PSIP_2016_12_flat"=unchanged after 2017
    tech_scen_id='PSIP_2016_12',
    # '1'=low, '2'=high, '3'=reference, 'EIA_ref'=EIA-derived reference level, 'hedged'=2020-2030 prices from Hawaii Gas
    fuel_scen_id='unhedged_2016_11_22',
    # note: 'unhedged_2016_11_22' is basically the same as 'PSIP_2016_09', but derived directly from EIA and includes various LNG options
    # Blazing a Bold Frontier, Stuck in the Middle, No Burning Desire, Full Adoption,
    # Business as Usual, (omitted or None=none)
    ev_scenario = 'PSIP 2016-12',
    # should the must_run flag be converted to set minimum commitment for existing plants?
    enable_must_run = 0,
    # list of technologies to exclude (currently CentralFixedPV, because we don't have the logic
    # in place yet to choose between CentralFixedPV and CentralTrackingPV at each site)
    exclude_technologies = ('CentralFixedPV', 'Lake_Wilson'),
    base_financial_year = 2016,
    interest_rate = 0.06,
    discount_rate = 0.03,
    # used to convert nominal costs in the tables to real costs
    inflation_rate = 0.025,
    # maximum type of reserves that can be provided by each technology (if restricted);
    # should be a list of tuples of (technology, reserve_type); if not specified, we assume
    # each technology can provide all types of reserves; reserve_type should be "none",
    # "contingency" or "reserve"
    max_reserve_capability=[('Battery_4', 'regulation'), ('Battery_6', 'regulation'), ('Battery_Conting', 'contingency')],
)

# # battery data from 2016-12-23 PSIP report (pp. J-87 - J-88)
# # note: we use the 4h battery to compare to the PSIP, even though the 6h battery is probably a better choice
# # this was used for main model runs from 2017-07-20 onward
# # TODO: store this in the back-end database
# psip_nominal_battery_cost_per_kwh = [  # years 2016-2045
#     660, 615, 565, 524,
#     487, 461, 440, 422, 406, 393, 382, 372, 363, 355,
#     349, 343, 338, 333, 329, 326, 323, 320, 317, 315,
#     313, 312, 310, 309, 307, 306,
# ]
# # below is for 6h batteries, from 2016-12-23 PSIP report (pp. J-89 - J-90)
# # these are the same as in the 2016-04-01 PSIP app. J,
# # which were used for the main model runs from 2017-05 forward
# # psip_nominal_battery_cost_per_kwh = [  # years 2016-2045530
# #     530, 493, 454, 421,
# #     391, 371, 353, 339, 326, 316, 306, 298, 291, 285,
# #     280, 275, 271, 268, 264, 262, 259, 257, 255, 253,
# #     252, 250, 249, 248, 247, 246
# # ]
# psip_battery_years = range(2016, 2045+1)
# psip_battery_cost_per_mwh = [
#     1000.0 * nom_cost * 1.018**(args["base_financial_year"] - year)
#         for year, nom_cost in zip(psip_battery_years, psip_nominal_battery_cost_per_kwh)
# ]

# # TODO: retire and replace with cheaper model after 15 years
# args.update(
#     BATTERY_CAPITAL_COST_YEARS = psip_battery_years,
#     battery_capital_cost_per_mwh_capacity_by_year = psip_battery_cost_per_mwh,
#     battery_n_years=15,
#     # battery_n_cycles=365*15,
#     battery_max_discharge=1.0,
#     battery_min_discharge_time=4,  # 6 for 6h battery
#     battery_efficiency=0.88,  # 80% for 6h in 2016-12 report, but 88% for 6h in 2016-04 report?
# )

# electrolyzer data from centralized current electrolyzer scenario version 3.1 in
# http://www.hydrogen.energy.gov/h2a_prod_studies.html ->
# "Current Central Hydrogen Production from PEM Electrolysis version 3.101.xlsm"
# and
# "Future Central Hydrogen Production from PEM Electrolysis version 3.101.xlsm" (2025)
# (cited by 46719.pdf)
# note: we neglect land costs because they are small and can be recovered later
# TODO: move electrolyzer refurbishment costs from fixed to variable

# liquifier and tank data from http://www.nrel.gov/docs/fy99osti/25106.pdf

# fuel cell data from http://www.nrel.gov/docs/fy10osti/46719.pdf

inflate_1995 = (1.0+args["inflation_rate"])**(args["base_financial_year"]-1995)
inflate_2007 = (1.0+args["inflation_rate"])**(args["base_financial_year"]-2007)
inflate_2008 = (1.0+args["inflation_rate"])**(args["base_financial_year"]-2008)
h2_lhv_mj_per_kg = 120.21   # from http://hydrogen.pnl.gov/tools/lower-and-higher-heating-values-fuels
h2_mwh_per_kg = h2_lhv_mj_per_kg / 3600     # (3600 MJ/MWh)

current_electrolyzer_kg_per_mwh=1000.0/54.3    # (1000 kWh/1 MWh)(1kg/54.3 kWh)   # TMP_Usage
current_electrolyzer_mw = 50000.0 * (1.0/current_electrolyzer_kg_per_mwh) * (1.0/24.0)   # (kg/day) * (MWh/kg) * (day/h)    # design_cap cell
future_electrolyzer_kg_per_mwh=1000.0/50.2    # TMP_Usage cell
future_electrolyzer_mw = 50000.0 * (1.0/future_electrolyzer_kg_per_mwh) * (1.0/24.0)   # (kg/day) * (MWh/kg) * (day/h)    # design_cap cell

current_hydrogen_args = dict(
    hydrogen_electrolyzer_capital_cost_per_mw=144641663*inflate_2007/current_electrolyzer_mw,        # depr_cap cell
    hydrogen_electrolyzer_fixed_cost_per_mw_year=7134560.0*inflate_2007/current_electrolyzer_mw,         # fixed cell
    hydrogen_electrolyzer_variable_cost_per_kg=0.0,       # they only count electricity as variable cost
    hydrogen_electrolyzer_kg_per_mwh=current_electrolyzer_kg_per_mwh,
    hydrogen_electrolyzer_life_years=40,                      # plant_life cell

    hydrogen_fuel_cell_capital_cost_per_mw=813000*inflate_2008,   # 46719.pdf
    hydrogen_fuel_cell_fixed_cost_per_mw_year=27000*inflate_2008,   # 46719.pdf
    hydrogen_fuel_cell_variable_cost_per_mwh=0.0, # not listed in 46719.pdf; we should estimate a wear-and-tear factor
    hydrogen_fuel_cell_mwh_per_kg=0.53*h2_mwh_per_kg,   # efficiency from 46719.pdf
    hydrogen_fuel_cell_life_years=15,   # 46719.pdf

    hydrogen_liquifier_capital_cost_per_kg_per_hour=inflate_1995*25600,       # 25106.pdf p. 18, for 1500 kg/h plant, approx. 100 MW
    hydrogen_liquifier_fixed_cost_per_kg_hour_year=0.0,   # unknown, assumed low
    hydrogen_liquifier_variable_cost_per_kg=0.0,      # 25106.pdf p. 23 counts tank, equipment and electricity, but those are covered elsewhere
    hydrogen_liquifier_mwh_per_kg=10.0/1000.0,        # middle of 8-12 range from 25106.pdf p. 23
    hydrogen_liquifier_life_years=30,             # unknown, assumed long

    liquid_hydrogen_tank_capital_cost_per_kg=inflate_1995*18,         # 25106.pdf p. 20, for 300000 kg vessel
    liquid_hydrogen_tank_minimum_size_kg=300000,                       # corresponds to price above; cost/kg might be 800/volume^0.3
    liquid_hydrogen_tank_life_years=40,                       # unknown, assumed long
)

# future hydrogen costs; could be used for alternative scenario (see future_hydrogen below)
future_hydrogen_args = current_hydrogen_args.copy()
future_hydrogen_args.update(
    hydrogen_electrolyzer_capital_cost_per_mw=58369966*inflate_2007/future_electrolyzer_mw,        # depr_cap cell
    hydrogen_electrolyzer_fixed_cost_per_mw_year=3560447*inflate_2007/future_electrolyzer_mw,         # fixed cell
    hydrogen_electrolyzer_variable_cost_per_kg=0.0,       # they only count electricity as variable cost
    hydrogen_electrolyzer_kg_per_mwh=future_electrolyzer_kg_per_mwh,
    hydrogen_electrolyzer_life_years=40,                      # plant_life cell

    # table 5, p. 13 of 46719.pdf, low-cost
    # ('The value of $434/kW for the low-cost case is consistent with projected values for stationary fuel cells')
    hydrogen_fuel_cell_capital_cost_per_mw=434000*inflate_2008,
    hydrogen_fuel_cell_fixed_cost_per_mw_year=20000*inflate_2008,
    hydrogen_fuel_cell_variable_cost_per_mwh=0.0, # not listed in 46719.pdf; we should estimate a wear-and-tear factor
    hydrogen_fuel_cell_mwh_per_kg=0.58*h2_mwh_per_kg,
    hydrogen_fuel_cell_life_years=26,
)

args.update(current_hydrogen_args)

args.update(
    pumped_hydro_headers=[
        'ph_project_id', 'ph_load_zone', 'ph_capital_cost_per_mw',
        'ph_project_life', 'ph_fixed_om_percent',
        'ph_efficiency', 'ph_inflow_mw', 'ph_max_capacity_mw'],
    pumped_hydro_projects=[
        ['Lake_Wilson', 'Oahu', 2800*1000+35e6/150, 50, 0.015, 0.77, 10, 150],
    ]
)

args.update(
    rps_targets = {2015: 0.15, 2020: 0.30, 2030: 0.40, 2040: 0.70, 2045: 1.00}
)

# data definitions for alternative scenarios
# TODO: create dummy additional battery projects that can't provide reserves,
# and add a cost to the main battery projects
# TODO: add a second pass to validate results? (not for this draft)
alt_args = [
    # dict(), # no base scenario
    # dict(time_sample='tiny', inputs_dir='inputs_tiny') # no tiny scenario
]

# make alternate directories with different reserve modes for load-shifting batteries
for ls_res_type in ['none', 'contingency', 'regulation']:
    caps = []
    for (b, rt) in args['max_reserve_capability']:
        if b in {'Battery_4', 'Battery_6'}:
            rt = ls_res_type
        caps.append((b, rt))
    alt_args.append(dict(
        max_reserve_capability=caps,
        inputs_dir=os.path.join('inputs', ls_res_type)
    ))

# files created by our standard export script, but not needed for this tutorial
# (used with obsolete modules or modules that are unused here)
unused_inputs = [
    'pumped_hydro.csv', 'hydrogen.dat', 'gen_timepoint_commit_bounds.csv',
    'ev_fleet_info_advanced.csv', 'ev_charging_bids.csv', 'ev_share.csv'
]

for a in alt_args:
    active_args = args.copy()
    active_args.update(a)
    scenario_data.write_tables(**active_args)
    for f in unused_inputs:
        f_path = os.path.join(
            active_args['inputs_dir'], active_args.get('inputs_subdir', ''), f
        )
        if os.path.exists(f_path):
            print("Deleting {}.".format(f_path))
            os.remove(f_path)
