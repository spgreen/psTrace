import statistics


def five_number_summary(number_list):
    """
    Finds the minimum, lower quartile (LQ), median, upper quartile (UQ) and maximum elements from a list of numbers. 
    It also calculates the upper threshold based on the following equation:  threshold = UQ + 1.5 * (UQ - LQ) 
    Return a dictionary containing the five number summary and threshold with the following key values: 
        min, lower_quartile, median, upper_quartile, max, threshold
    :param number_list: 
    :return: 
    """
    number_list_size = len(number_list)
    try:
        number_list = sorted(number_list)
    except:
        print("Error: Invalid list elements found")
        return {"min": "", "lower_quartile": "", "median": "", "upper_quartile": "", "max": "", "threshold": ""}
    # Splits odd or even sized lists into their respective upper and lower sections
    # Odd sized list
    if number_list_size % 2:
        upper_index = int(number_list_size/2) + 1
        lower_index = upper_index - 1
    else:
        upper_index = int(number_list_size/2)
        lower_index = upper_index
    try:
        lower_quartile = statistics.median(number_list[:lower_index])
        upper_quartile = statistics.median(number_list[upper_index:])
        threshold = upper_quartile + 1.5 * (upper_quartile - lower_quartile)
        return {"min": number_list[0],
                "lower_quartile": lower_quartile,
                "median": statistics.median(number_list),
                "upper_quartile": upper_quartile,
                "max": number_list[-1],
                "threshold": threshold}
    except TypeError:
        print("Error: Not int or float variables")
    except statistics.StatisticsError:
        print("Error: Not enough elements within list")
    return {"min": "", "lower_quartile": "", "median": "", "upper_quartile": "", "max": "", "threshold": ""}