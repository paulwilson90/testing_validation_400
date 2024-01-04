import json
import math

RED = '\033[31m'
REDEND = '\033[0m'


def get_uld(elevation, flap, weight):
    """Gets the ULD by interpolating and using index locations from the QRH
    It grabs the weight one tonne up and below and the elevation INDEX position one up and below.
    It then interpolates using the percentage of the remaining index location."""
    weight_tonnes = weight / 1000
    flap = str(int(flap))
    wt_up = str(math.ceil(float(weight_tonnes)))
    wt_down = str(math.floor(float(weight_tonnes)))
    with open('ulds_q400.json') as ulds:
        uld_ = json.load(ulds)
    elevation_up = math.ceil(elevation)
    elevation_down = math.floor(elevation)
    # interpolating with the upper weight of the two elevation figures
    wt_up_up_data = uld_[flap][wt_up][elevation_up]
    wt_up_dwn_data = uld_[flap][wt_up][elevation_down]
    uld_up_wt = round(wt_up_dwn_data + ((wt_up_up_data - wt_up_dwn_data) * (elevation - elevation_down)))
    # interpolating with the lower weight of the two elevation figures
    wt_dwn_up_data = uld_[flap][wt_down][elevation_up]
    wt_dwn_dwn_data = uld_[flap][wt_down][elevation_down]
    uld_dwn_wt = round(wt_dwn_dwn_data + ((wt_dwn_up_data - wt_dwn_dwn_data) * (elevation - elevation_down)))
    # interpolating for weight between the two elevation interpolated figures
    final_uld = round(uld_dwn_wt + (uld_up_wt - uld_dwn_wt) * (float(weight_tonnes) - int(wt_down)))

    return final_uld


def wind_correct_formulated(ULD, wind_comp):
    """For every ULD entry to the wind chart above 700, add 0.003m on top of 3.8 for every knot head
    for every ULD entry to the wind chart above 700, add 0.009667m on top of 12 for every knot tail"""
    amount_above_700 = ULD - 700
    if wind_comp > 0:  # if its a headwind
        factor_above_uld = amount_above_700 * 0.003
        wind_corrected_ULD = round(ULD - (wind_comp * (3.8 + factor_above_uld)))
    else:  # if its a tailwind
        factor_above_uld = amount_above_700 * 0.009667
        wind_corrected_ULD = ULD - round((wind_comp * (12 + factor_above_uld)))

    if wind_comp < -10:  # if the wind is more than 10 knot tail, add 1.6% for every knot over 10t
        factor_above_uld = amount_above_700 * 0.009667
        ten_tail_ULD = ULD - round((-10 * (12 + factor_above_uld)))
        wind_corrected_ULD = int(ten_tail_ULD * (1 + ((abs(wind_comp) - 10) * 1.6) / 100))

    return int(wind_corrected_ULD)


def slope_corrected(slope, wind_corrected_ld):
    """If the slope is greater than 0, the slope is going uphill so the distance will be shorter
    IF the slope is less than 0 however, the slope is downhill and the distance increases.
    For every 1% slope downhill (Negative slope), increase the ULD by 9.25% 630
    For every 1% slope uphill (Positive slope), decrease the ULD by 6.5%"""
    #  if the slope is downhill
    if slope < 0:
        slope_correct = wind_corrected_ld + (wind_corrected_ld * (abs(slope) * 0.0925))
    #  if the slope is uphill
    else:
        slope_correct = wind_corrected_ld - (wind_corrected_ld * (abs(slope) * 0.065))
    return slope_correct


def get_v_speeds(weight, flap, vapp_addit, ice):
    flap = str(flap)
    weight = str((math.ceil(weight / 500) * 500) / 1000)
    print(weight)
    with open('ref_speeds.json') as file:
        f = json.load(file)
    vref = f[flap][weight]
    vapp = int(vref) + vapp_addit
    if flap == "15":
        vref_ice = vref + 20
    else:
        vref_ice = vref + 15
    if ice == "On":
        vapp = vref_ice

    return vapp, vref, vref_ice


def vapp_corrections(wind_slope_ld, vref, vref_addit):
    """Take the wind and slope corrected landing distance and apply increase in distance by using formula
    vpp^2 / vref^2 which gives the multiplier to the LD"""

    percent_increase = (vref + vref_addit) ** 2 / vref ** 2
    print("Added", str(percent_increase)[2:4], "percent increase to landing distance")

    vapp_adjusted_ld = wind_slope_ld * percent_increase

    return vapp_adjusted_ld, percent_increase


def reduced_np_addit(power, vapp_adjusted_ld):
    """Will add the 6% if reduced NP"""
    if power == 'RDCP':
        prop_setting_adjusted = vapp_adjusted_ld * 1.06
    else:
        prop_setting_adjusted = vapp_adjusted_ld

    return int(prop_setting_adjusted)


def ice_protect_addit(flap, prop_adjusted_ld):
    """If INCR REF switch on, add 25% for flap 15 and 20% for flap 35. """
    flap = str(int(flap))
    if flap == "15":
        ice_protect_adjusted_ld = prop_adjusted_ld * 1.25
    else:
        ice_protect_adjusted_ld = prop_adjusted_ld * 1.20

    return ice_protect_adjusted_ld


def company_addit_dry_wet(wet_dry, ice_on_ld, ice_off_ld):
    """Adding 43% to the prop_adjusted_ld if dry and an additional 15% on top of that if wet 1222 = 1465
    43% is approximate figure as it is actually divided by 0.7"""
    if wet_dry == "Wet":
        ICE_ON_wet_dry_adjusted_ld = (ice_on_ld / 0.7) * 1.15
        ICE_OFF_wet_dry_adjusted_ld = (ice_off_ld / 0.7) * 1.15
    else:
        ICE_ON_wet_dry_adjusted_ld = ice_on_ld / 0.7
        ICE_OFF_wet_dry_adjusted_ld = ice_off_ld / 0.7

    return int(ICE_ON_wet_dry_adjusted_ld), int(ICE_OFF_wet_dry_adjusted_ld)


def get_torque_limits(temp, pressure_alt, vapp, bleed):
    if temp < 0:
        temp = 0
    if temp > 48:
        temp = 48
    if pressure_alt > 6000:
        pressure_alt = 6000
    if pressure_alt < 0:
        pressure_alt = 0
    temp = str(temp)
    pressure_alt = pressure_alt / 500
    with open(f'takeoff_torques_bleed_{bleed}.json') as file:
        torque = json.load(file)

    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)
    power = ["NTOP", "MTOP"]
    for lst in range(len(power)):
        # interpolating with the upper temp of the two elevation figures
        temp_up_up_data = torque[temp_up][elev_up][lst]
        temp_up_dwn_data = torque[temp_up][elev_down][lst]
        temp_up_wt = temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down))
        # interpolating with the lower temp of the two elevation figures
        temp_dwn_up_data = torque[temp_down][elev_up][lst]
        temp_dwn_dwn_data = torque[temp_down][elev_down][lst]
        temp_dwn_wt = temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down))

        torque_limit = (temp_up_wt + temp_dwn_wt) / 2

        power[lst] = torque_limit
    ntop = power[0]
    mtop = power[1]
    if ntop > 90.3:
        ntop = 90.3
    if mtop > 100:
        mtop = 100

    if vapp > 100:
        amount_over = vapp - 120
        for_every_three = amount_over / 3
        add_point_one = for_every_three * 0.1
        ntop = ntop + add_point_one
        mtop = mtop + add_point_one

    else:
        amount_under = 120 - vapp
        for_every_three = amount_under / 3
        subtract_point_one = for_every_three * 0.1
        ntop = ntop - subtract_point_one
        mtop = mtop - subtract_point_one

    if ntop > 90.3:
        ntop = 90.3
    if mtop > 100:
        mtop = 100

    return round(ntop, 2), round(mtop, 2)


def get_wat_limit(temp, flap, propeller_rpm, bleed, pressure_alt, test_case):
    """Take in the temp, flap, bleed position and pressure altitude as parameters
    and return the max landing weight.
    Also trying to keep indexes in range as some temperatures and pressure altitudes are off charts.
    The minimum pressure alt for the chart is 0 and the max is 4000.
    The minimum temperature is 0 and the max is 48, even after the 11 degree addit"""
    off_chart_limits = False

    flap = str(int(flap))
    if pressure_alt < 0:
        pressure_alt = 0
        off_chart_limits = True
    else:
        if pressure_alt > 4000:
            pressure_alt = 4000 / 500
            off_chart_limits = True
        else:
            pressure_alt = pressure_alt / 500
    if propeller_rpm == "RDCP":
        rpm = "850"
    else:
        rpm = "1020"
    if bleed == "On":
        temp = int(temp) + 11

    if temp > 48:
        temp = str(48)
        off_chart_limits = True
        if pressure_alt > 2:
            pressure_alt = 2
    else:
        if temp < 0:
            temp = str(0)
            off_chart_limits = True
        else:
            temp = str(temp)
    if flap == "35":
        ga_flap = "15"
    else:
        ga_flap = "10"

    with open(f'wat_f{ga_flap}.json') as r:
        wat = json.load(r)
    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)

    # interpolating with the upper temp of the two elevation figures
    temp_up_up_data = wat[rpm][temp_up][elev_up]
    temp_up_dwn_data = wat[rpm][temp_up][elev_down]
    temp_up_wt = round(temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down)))
    # interpolating with the lower temp of the two elevation figures
    temp_dwn_up_data = wat[rpm][temp_down][elev_up]
    temp_dwn_dwn_data = wat[rpm][temp_down][elev_down]
    temp_dwn_wt = round(temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down)))

    wat_limit = int((temp_up_wt + temp_dwn_wt) / 2)
    MLDW = 28009

    return wat_limit, MLDW, off_chart_limits


def max_landing_wt_lda(lda, ice, ICE_ON_dry_wet, ICE_OFF_dry_wet, wet_dry, flap, weight, unfact_uld):
    """Find the ratio between the landing distance required and the unfactored ULD which returns a multiplier ratio
    Divide the landing distance available by the ratio to find the relative unfactored ULD
    Get the difference between the maximum (LDA based) ULD and the current ULD and divide by 23 for flap 15 or 20.5 for
    flap 35 and multiply by 1000 (This is ULD diff for every tonne) this will give the weight to add onto the
    current landing weight which will give the max field landing weight. """
    flap = str(flap)
    if ice == "On":
        ld_required = ICE_ON_dry_wet
    else:
        ld_required = ICE_OFF_dry_wet

    if flap == "15":
        ratio = ld_required / unfact_uld
        print(f"flap {flap} ratio is {ratio} because LDR is {ld_required} and unfact ULD is {unfact_uld}")
        max_unfact_uld = lda / ratio
        print(f"max unfactoreds uld is {max_unfact_uld}")
        diff_between_ulds = max_unfact_uld - unfact_uld
        print("difference is", diff_between_ulds)
        final = ((diff_between_ulds / 23) * 1000) + weight
        print('final is', final)
    else:
        ratio = ld_required / unfact_uld
        max_unfact_uld = lda / ratio
        diff_between_ulds = max_unfact_uld - unfact_uld
        final = ((diff_between_ulds / 20.5) * 1000) + weight
    print("Max Field weight", int(final))
    return int(final)


def final_max_weight(max_wat, max_field, MLDW, off_chart):
    """Find and return the lowest weight out of all provided. Also add * to any code where the wat weight
    used a parameter that was off chart."""
    # f means field, s means struc, c means climb
    if max_wat < max_field:
        max_weight = max_wat
        code_max = "(c)"
    else:
        max_weight = max_field
        code_max = "(f)"
    if max_weight > MLDW:
        max_weight = MLDW
        code_max = "(s)"

    if off_chart:
        max_weight = str(max_weight) + code_max + "^"
    else:
        max_weight = str(max_weight) + code_max
    return max_weight
