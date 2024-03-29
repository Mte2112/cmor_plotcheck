import os
import sys
import glob
import time
import numpy as np
import xarray as xr
import pandas as pd
import dataframe_image as dfi

from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from datetime import date
from matplotlib import pyplot as plt

from cmor_plot.cmor_plot.cptools import Tools
from cmor_plot.cmor_plot.cptools import Plotting
from cmor_plot.cmor_plot.cptools import Statistics

# Time entire process
start = time.time()

# Collect command line arguments
options = Tools.readOptions(sys.argv[1:])
runE2 = options.EXrun
runE3 = options.E3run
figure_name = options.figure_name
hist_option = options.histogram
variable = options.variable
start_year = options.start_year
end_year = options.end_year
risk_threshold = options.risk_threshold

# Change directory and set paths for looping
outdir = os.getcwd()
os.chdir(outdir)
allvarsE2 = runE2 + "*/*/*/*"
allvarsE3 = runE3 + "*/*/*/*"

# Initialize table counter and list, and list of tests
comparison_counter = 0
table_pdf_list = []
table_title_list = []
test_list = []

# Set variables for plotting
valid_range = True
plot_num = 0

# Loop through the E3 directory 
for direc3 in glob.glob(allvarsE3):

    # Call 'get_sample' for E3, save filename and open dataset
    fileE3 = Tools.get_sample(direc3, outdir)
    
    if ('/fx/' in fileE3) | ('/fy/' in fileE3) | ('/Ofx/' in fileE3) | ('/Ofy/' in fileE3):
        None
    else:

        # Read in properly formatted file
        dsE3 = Tools.read_netcdf(fileE3)
        
        # Get relevant varname & frequency
        freq = direc3.split("/")[-4]
        varname = direc3.split("/")[-3]

        # Compare variable to file name to command line input variable
        if (variable is None) or (varname in variable):

            # Collect info from directory structure
            gride3 = direc3.split("/")[-2]
            modelv2 = runE2.split('CMIP6')[1].split('/')[3]
            modelv3 = direc3.split("/")[-7]
            
            # Try to find the same var/freq in E2
            # start here-- basically try to get the same file using the freq and varname defined earlier. if exception, plot no data
            e3version = direc3.split("/")[-1]
            e2path_short = runE2 + direc3.split(e3version)[0].split(runE3)[1]
            e2path_full = e2path_short + "*"
            direc2 = glob.glob(e2path_full)
            if len(direc2) > 0:
                direc2 = direc2[0]
                os.chdir(direc2) # if this fails, there was no path found (aka no matching data)
                fileE2 = Tools.get_sample(direc2, outdir)

                # Create e2 dataset
                dsE2 = Tools.read_netcdf(fileE2)

                # Verify that E2 variable exists, and carry on
                varexist = 1
                
            else:

                # Check if there is a native grid E2 match to E3 regridded
                if gride3 == "gr":
                    e2path_full_native = e2path_full.replace("/gr/", "/gn/")
                    direc2 = glob.glob(e2path_full_native)
                    if len(direc2) > 0:
                        direc2 = direc2[0]
                        os.chdir(direc2) # if this fails, there was no path found (aka no matching data)
                        fileE2 = Tools.get_sample(direc2, outdir)

                        # Read in properly formatted E2 file
                        dsE2 = Tools.read_netcdf(fileE2)

                        # Verify that E2 variable exists, and carry on
                        varexist = 1
                else:   
                    print("No E2 match found for " + fileE3.split('/')[-1] + ", skipping...")
                    dsE2 = None
                    varexist = 0
                    
            # Check for num dimensions
            dsE3 = Tools.check_dim(dsE3, varname)
            if varexist == 1:
                dsE2 = Tools.check_dim(dsE2, varname)
            
            # Title for primary plot
            years = fileE3.split('_')[-1].split('.')[0]
            m3title = direc3.split("/")[-7] + "\n" + direc3.split("/")[-6] + " " + direc3.split("/")[-5] + " " \
                    + direc3.split("/")[-2] + " " + direc3.split("/")[-1] + " " + "(" + years + ")"
            if varexist == 1:
                m2title = direc2.split("/")[-7] + "\n" + direc2.split("/")[-6] + " " + direc2.split("/")[-5] + " " \
                        + direc2.split("/")[-2] + " " + direc2.split("/")[-1] + " " + "(" + years + ")"

            # Title for histogram
            hist_title = 'Comparison ' + str(comparison_counter) + '\n' \
                            + direc2.split("/")[-7] + ' ' + direc2.split("/")[-6] + " " + direc2.split("/")[-5] + " " \
                            + direc2.split("/")[-2] + " " + direc2.split("/")[-1] + " " + "(" + years + ")\n" \
                            + direc3.split("/")[-7] + ' ' + direc3.split("/")[-6] + " " + direc3.split("/")[-5] + " " \
                            + direc3.split("/")[-2] + " " + direc3.split("/")[-1] + " " + "(" + years + ")" \
            
            # Get cbar labels
            try:
                labele3 = 'Mean' + dsE3[varname].attrs["units"]
            except:
                labele3 = 'Mean' + varname
            try:
                labele2 = 'Mean' + dsE2[varname].attrs["units"]
            except:
                labele2 = 'Mean' + varname

            # Filter by year
            if (start_year is not None) and (end_year is not None):

                # Collect start / end year from files
                file_start = int(years.split('-')[0][:4])
                file_end = int(years.split('-')[1][:4])

                # Check if time range is valid
                if (start_year in range(file_start, file_end+1)) and (end_year in range(file_start, file_end+1)):\

                    # If it is, update variable and slice datasets
                    valid_range = True
                    dsE3 = dsE3.sel(time=slice(date(start_year, 1, 1), date(end_year, 1, 1)))
                    dsE2 = dsE2.sel(time=slice(date(start_year, 1, 1), date(end_year, 1, 1)))

                else:
                    valid_range = False

            # Continue if no start / end year specified with command line arguments
            else:
                pass

            ##### Only plot / calculate for a valid time range #####
            if valid_range is True:

                # Increment number 
                plot_num += 1

                ### Create heatmap ###
                Plotting.heatmap(dsE2, dsE3, varname, varexist, m2title, m3title, comparison_counter)

                # Calculate formatted and color-coded statistics tables
                table_title = 'Comparison ' + str(comparison_counter) + '<br>Variable: ' + varname\
                                + '<br>E2 File: ' + m2title + '<br>' + 'E3 File: ' + m3title
                table_title_list.append(table_title)
                formatted_df, color_df, tests = Statistics.stats_tables(dsE2, dsE3, risk_threshold, table_title)
                test_list.append(tests)

                # Create intermediate PNG files for each table
                table_name = 'intermediate_table_' + str(comparison_counter) + '.png'
                dfi.export(color_df, table_name)
                table_pdf_list.append(table_name)
                comparison_counter += 1

                # Print KL divergence between E2 and E3
                E2_vals = list(dsE2.data_vars.items())[-1][1].values.flatten()
                E3_vals = list(dsE3.data_vars.items())[-1][1].values.flatten()
                kl_divergence = Statistics.KL_divergence(E2_vals, E3_vals)

                # Print files, KL divergence, and formatted table to stdout
                print(f'\nE2 File: {m2title}\n\nE3 File: {m3title}')
                print(f'\nKL Divergence: {kl_divergence}')
                print(formatted_df)

                # Create histogram if -hist option used
                if hist_option is True:

                    ### Plot histogram of E2 and E3 data ###
                    Plotting.histogram(E2_vals, E3_vals, hist_title, varname)

                # Default is to not plot histogram
                else:
                    pass

            ##### Don't perform any operations on empty dataset #####
            else:
                # Collect start / end year from files
                file_start = int(years.split('-')[0][:4])
                file_end = int(years.split('-')[1][:4])

        # Don't analyze files for variables not included in query
        else:
            pass

# Only save files and create tables if there's at least a single valid plot / file
if plot_num > 0:

    # Name file, save all plots
    Tools.save_image(figure_name + '_plots.pdf')

    # Create overall test table, add to table_pdf_list
    variable = list(dsE3.data_vars.items())[-1][0]
    var_title = 'Statistic'
    test_table = pd.DataFrame({var_title: ['Mean', 'Median', 'Minimum', 'Maximum', 'Standard Deviation']}).set_index([var_title])
    test_table_title = "\u0332".join('Key:') + '\n\n'
    col_counter = 0

    # Add columns for each comparison
    for i in range(len(test_list)):
        test_table['Comparison ' + str(col_counter)] = test_list[i]
        test_table_title += table_title_list[i].replace('\n', ' ').replace('<br>', '\n') + '\n\n'
        col_counter += 1

    # Calculate risk number
    risky_values = sum(test_table[test_table > risk_threshold].count())
    num_rows = len(test_table)
    num_cols = len(test_table.columns)
    num_values = num_rows * num_cols
    risk_fraction = risky_values / num_values
    risk_percentage = '{:.1%}'.format(risk_fraction)

    # Format test table
    format_dict = {}
    for col_i in test_table.columns: format_dict[col_i] = '{:.3f}'
    red_bound = [100 if (risk_threshold*3 <100) else risk_threshold*3][0]
    color_ranges = {'green': [0, risk_threshold],
                    'yellow': [risk_threshold, risk_threshold*2],
                    'orange': [risk_threshold*2, red_bound],
                    'red': [red_bound, np.inf]}
    color_key = '<br><br>Key for color ranges:<br>'
    for key, value in color_ranges.items():
        color_key += key + ': ' + str(value) + '<br>'
    test_table_caption = 'Percent Difference between Various Runs<br>Risk Percentage: '+ risk_percentage\
                        + color_key
    test_table = test_table.style.apply(lambda x: ['background: green' if (v < color_ranges['green'][1]) else '' for v in x], axis = 1)\
                                 .apply(lambda x: ['background: yellow' if (color_ranges['yellow'][0] <= v < color_ranges['yellow'][1]) else '' for v in x], axis = 1)\
                                 .apply(lambda x: ['background: orange' if (color_ranges['orange'][0] <= v < color_ranges['orange'][1]) else '' for v in x], axis = 1)\
                                 .apply(lambda x: ['background: red' if (v >= color_ranges['red'][0]) else '' for v in x], axis = 1)\
                                 .format(format_dict)\
                                 .set_caption(test_table_caption)

    # Save test table as png, add to list of table figures
    dfi.export(test_table, 'test_table.png')
    table_pdf_list.append('test_table.png')

    # Create png for key
    width = 512
    height = len(test_list) * 250
    message = test_table_title
    img = Image.new('RGB', (width, height), color='white')
    font = ImageFont.truetype("Helvetica", 12)
    imgDraw = ImageDraw.Draw(img)
    imgDraw.text((10, 10), message, fill=(0, 0, 0), font=font)
    img.save('key.png')
    table_pdf_list.append('key.png')

    # Consolidate all tables into a single file
    pdf = FPDF()
    pdf.set_auto_page_break(0)
    for image in table_pdf_list:

        # Add formatted table PNG to overall PDF file
        pdf.set_font(family='Arial', style='B', size=200)
        title = 'Table'
        pdf.set_title(title)
        pdf.add_page()
        x = pdf.get_x()
        y = pdf.get_y()
        w = pdf.get_string_width(title)
        pdf.image(image, x=x, y=y, w=w)

        # Delete intermediate table files
        os.remove(image)

    # Save PDF file including all tables
    pdf.output(figure_name + '_tables.pdf', 'F')

    # Print key for overall table (color-coded) to command line
    color_key = '\nKey for color ranges:\n(Values represent percent difference in aggregate values between E2 and E3 runs)\n'
    for key, value in color_ranges.items():
        color_key += Tools.format_text(key, key) + ': ' + str(value) + '\n'
    print(color_key)

    # Calculate overall time
    end = time.time()
    duration = round(end - start, 3)
    print(f'Total time: {duration} seconds')

# No valid data to work with
else:
    print('No usable data for given input')