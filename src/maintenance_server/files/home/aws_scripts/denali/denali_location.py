#
# denali_location.py
#

# This file stores the data center location data used by denali
#
# Up-to-date list can be found with this query:
#
#    denali --dao=LocationDao --name="*" --fields=name,location_id --sort=location_id
#

#                0          1           2       3       4          5       6       7       8       9
dc_location = [
               "DMZ.UT1", "SJ1",      "SJ2",  "OAK1", "DAL",     "DA2",  "DA3",  "LON1", "LON3", "ORM1",      #   0-9
               "VA1",     "VA2",      "VA3",  "LON2", "LON4",    "SJ3",  "",     "",     "SD1",  "CPH1",      #  10-19
               "",        "VA5",      "BOS1", "LOF1", "LOF2",    "ORM2", "SYD1", "HOU1", "EGM1", "CPH2",      #  20-29
               "LA1",     "NY1",      "NY2",  "NY3",  "PHX1",    "SD2",  "SJ4",  "SJ0",  "WIS1", "SF1",       #  30-39
               "SYD2",    "SF2",      "SF3",  "SF4",  "SF5",     "LA2",  "SB1",  "DA4",  "SJ6",  "BJG1",      #  40-49
               "PAR1",    "STK1",     "MUN1", "TYO1", "PTN1",    "CNU1", "HLA1", "TYO2", "LON5", "ML1",       #  50-59
               "SF6",     "DA5",      "NJ1",  "DUB1", "LON6",    "SIN1", "NJ2",  "LA3",  "NY6",  "SIN2",      #  60-69
               "SIN3",    "VA6",      "",     "MAI1", "SAO1",    "SF7",  "SJ5",  "VA4",  "LON7", "SV2",       #  70-79
               "OAK2",    "IND1-old", "HK1",  "HK2",  "HQ1",     "UT1",  "AMS1", "OR1",  "OH1",  "TX4",       #  80-89
               "SAO2",    "SYD3",     "CA1",  "IRL1", "TYO3",    "NY7",  "SD3",  "OR2",  "SJO",  "SEA1",      #  90-99
               "PNW",     "BOS2",     "PAR2", "PAR3", "MON1",    "MON2", "SYD4", "BRS1", "BOS3", "PAR4",      # 100-109
               "PAR5",    "GER1",     "LON",  "PAR6", "PAR7",    "SIN4", "LON8", "KR1",  "BJG2", "GOV1",      # 110-119
               "IN1",     "OLD_VA7",  "VA8", "HK3",   "IA1",     "SIN5", "AMS2", "IL1",  "WA1",  "TX1",       # 120-129
               "SJ7",     "WY1",      "UT2",  "LON9", "GER2",    "TYO4", "SAO3", "SYD5", "CAN2", "OH2",       # 130-139
               "SV3",     "DC7",      "AM6",  "BUCH1","VA7",     "CA3",  "SIN6", "CAN5", "CHN2", "CHN3",      # 140-149
               "VA10",    "CA13",     "GBR10","AUS6", "Magento", "AUS7", "AUS8", "AUS9", "CAN6", "CHN4",      # 150-159
               "CHN5",    "DEU4",     "FRA8", "FRA9", "FRA10",   "GBR11","GBR12","IA2",  "IND2", "IND3",      # 160-169
               "IND4",    "IRL3",     "JPN5", "KOR2", "KOR3",    "SWE1", "VA11", "VA12", "VA13", "BEL1",      # 170-179
               "OR4",     "ZAF2",     "ZAF1", "CHN6", "HKG4",    "JPN6", "AUS10","BRA4", "CA14", "CAN7",      # 180-189
               "CHE1",    "DEU5",     "FIN1", "GBR13","HKG5",    "IA3",  "IND5", "JPN7", "JPN8", "NLD4",      # 190-199
               "SC1",     "SGP7",     "TWN1", "ARE1", "ARE2",    "CHE2", "CHE3", "DEU6", "DEU7", "BHR1",      # 200-209
               "NOR1",    "NOR2",     "VA14", "IA4",  "IND6",                                                 # 210-214
              ]
