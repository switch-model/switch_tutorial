import os
from pyomo.environ import *

# Assume cogen capacity can be added to all thermal plants (fuel-based
# generators), using a heat rate of cogen_heat_rate (MMBtu/MWh) and a carrying
# cost of cogen_fixed_cost per MW per year.

def define_components(m):
    # input parameters defining the cogen technology (also see load_inputs())
    m.cogen_heat_rate = Param()
    m.cogen_fixed_cost = Param()

    # Define a collection of valid pairs of (fuel-based generator, operating period).
    # These are also the locations and periods where cogen capacity can exist
    def FUEL_BASED_GEN_PERIODS_init(m):
        valid_pairs = []
        for g in m.FUEL_BASED_GENS:
            for p in m.PERIODS_FOR_GEN[g]:
                valid_pairs.append((g, p))
        return valid_pairs
    m.FUEL_BASED_GEN_PERIODS = Set(dimen=2, initialize=FUEL_BASED_GEN_PERIODS_init)

    # note: switch_model.generators.core.dispatch already defines a
    # FUEL_BASED_GEN_TPS set showing valid (fuel-based gen, timepoint) pairs

    # Decide how much cogen capacity to have online each period and
    # how much power to produce during each timepiont
    m.CogenCapacity = Var(
        m.FUEL_BASED_GEN_PERIODS, within=NonNegativeReals
    )
    m.DispatchCogen = Var(
        m.FUEL_BASED_GEN_TPS, within=NonNegativeReals
    )

    # Don't allow cogen dispatch to exceed installed capacity
    def Max_DispatchCogen_rule(m, g, t):
        test = (m.DispatchCogen[g, t] <= m.CogenCapacity[g, m.tp_period[t]])
        return test
    m.Max_DispatchCogen = Constraint(
        m.FUEL_BASED_GEN_TPS, rule=Max_DispatchCogen_rule
    )

    # Don't allow cogen heat usage to exceed available waste heat
    def DispatchCogen_Available_Heat_rule(m, g, t):
        # Restrict cogen output to use only available heat.
        # When using switch_model.generators.core.no_commit, generator always
        # runs at full load heat rate; see no_commit code or
        # https://ars.els-cdn.com/content/image/1-s2.0-S2352711018301547-mmc1.pdf
        heat_input = m.DispatchGen[g, t] * m.gen_full_load_heat_rate[g]
        work_done = m.DispatchGen[g, t] * 3.412  # power output, converted to MMBtu
        rule = (
            m.DispatchCogen[g, t] * m.cogen_heat_rate    # heat used by cogen
            <= heat_input - work_done                    # heat available
        )
        return rule
    m.DispatchCogen_Available_Heat = Constraint(
        m.FUEL_BASED_GEN_TPS, rule=DispatchCogen_Available_Heat_rule
    )

    # calculate power output from cogen units in zone z in timepoint t
    def CogenZonalOutput_rule(m, z, t):
        total_output = sum(
            m.DispatchCogen[g, t]
            for g in m.FUEL_BASED_GENS
            if m.gen_load_zone[g] == z and t in m.TPS_FOR_GEN[g]
        )
        return total_output
    m.CogenZonalOutput = Expression(
        m.LOAD_ZONES, m.TIMEPOINTS,
        rule=CogenZonalOutput_rule
    )
    # Add cogen output to system generation balance
    m.Zone_Power_Injections.append('CogenZonalOutput')

    # Calculate fixed costs for all cogen units online in period p
    def CogenFixedCost_rule(m, p):
        total_capacity = sum(
            m.CogenCapacity[g, p]
            for g in m.FUEL_BASED_GENS
            if p in m.PERIODS_FOR_GEN[g]
        )
        return total_capacity * m.cogen_fixed_cost
    # Add fixed costs to model
    m.CogenFixedCost = Expression(
        m.PERIODS, rule=CogenFixedCost_rule
    )
    m.Cost_Components_Per_Period.append('CogenFixedCost')

def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'cogen.csv'),
        autoselect=True,
        param=(m.cogen_heat_rate, m.cogen_fixed_cost))
