'''
A script to (1) estimate H&Y disease stage score using itemized scores from UPDRS Part 3 and
(2) convert UDPRS to MDS-UPDRS scores using the method described by Goetz et al. (2012)

author: @Andrew Vo
'''

import pandas as pd

path = '/Users/Andrew/Documents/Research/Projects/qpn_data/'
df = pd.read_csv(path+'tabular/updrs.csv', header=0)

# calculate left and right side affected
df['left'] = (df['Updrs_3_3_lue value'] + df['Updrs_3_3_lle value'] + df['Updrs_3_4_l value'] +
              df['Updrs_3_5_l value'] + df['Updrs_3_6_l value'] + df['Updrs_3_8_l value'])

df['right'] = (df['Updrs_3_3_rue value'] + df['Updrs_3_3_rle value'] + df['Updrs_3_4_r value'] +
               df['Updrs_3_5_r value'] + df['Updrs_3_6_r value'] + df['Updrs_3_8_r value'])

# estimate hy score from updrs part 3
df[['hy_derived', 'updrs3_combined']] = pd.NA
# mask_complete = df['Complete?'] != 'Incomplete'
df.loc[((df['left'] == 0) | (df['right'] == 0)), 'hy_derived'] = 1
df.loc[(df['left'] > 0) & (df['right'] > 0) & (df['Updrs_3_12 value'] == 0), 'hy_derived'] = 2
df.loc[(df['left'] > 0) & (df['right'] > 0) & (df['Updrs_3_12 value'] > 0) & (df['Updrs_3_10 value'] == 0), 'hy_derived'] = 3
df.loc[(df['left'] > 0) & (df['right'] > 0) & (df['Updrs_3_12 value'] > 0) & (df['Updrs_3_10 value'] > 0) & (df['Updrs_3_10 value'] < 3), 'hy_derived'] = 4
df.loc[(df['left'] > 0) & (df['right'] > 0) & (df['Updrs_3_12 value'] > 0) & (df['Updrs_3_10 value'] > 0) & (df['Updrs_3_10 value'] >= 3), 'hy_derived'] = 5

# check if updrs version is new or old
cols_to_check = [
    'Part I: Non-Motor Aspects of Experiences of Daily Living (nM-EDL)',
    'Part II: Motor Aspects of Experiences of Daily Living (M-EDL)',
    'Part IV: Motor Complications'
]
mask_old = df[cols_to_check].isnull().all(axis=1)
mask_new = df[cols_to_check].notnull().any(axis=1)

# convert original uprds to mds-updrs
df.loc[mask_new, 'updrs3_combined'] = df['Part III: Motor Examination']
df.loc[mask_old & df['hy_derived'].isin([1, 2]), 'updrs3_combined'] = (df['Part III: Motor Examination'] * 1.2) + 2.3
df.loc[mask_old & (df['hy_derived'] == 3), 'updrs3_combined'] = (df['Part III: Motor Examination'] * 1.2) + 1.0
df.loc[mask_old & df['hy_derived'].isin([4, 5]), 'updrs3_combined'] = (df['Part III: Motor Examination'] * 1.1) + 7.5

# drop left and right cols
df.drop(columns=['left', 'right', 'hy_derived'], inplace=True)

# save result
df.to_csv(path+'tabular/updrs_modified.csv', index=False)
