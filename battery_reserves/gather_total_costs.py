import glob, os
import pandas as pd

# find all the total_cost files
search_pattern = os.path.join("outputs", "*", "total_cost.txt")

vals = pd.DataFrame()
for path in glob.glob(search_pattern):
    # use the subdirectory name as the scenario
    parts = path.split(os.sep)
    scen = parts[-2].replace("_", " ")
    tmp = pd.read_csv(path, header=None)
    vals.loc[scen, 'total cost'] = tmp.iloc[0, 0]

vals = vals.sort_index()

# There are 460,000 customers on Oahu
vals['cost per customer'] = vals['total cost']/460000

# Calculate difference from baseline
vals['savings vs baseline'] = vals.loc['battery bulk', 'cost per customer'] - vals['cost per customer']

output_path = os.path.join('outputs', 'savings_per_customer.csv')
vals.to_csv(output_path)
print("Saved total cost for all scenarios in {}:".format(output_path))
print(vals)
