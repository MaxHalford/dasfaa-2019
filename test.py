import sqlalchemy
import pandas as pd

uri = 'postgresql://postgres:admin@localhost:5432/tpcds'

engine = sqlalchemy.create_engine(uri)
con = engine.connect()
df = pd.read_sql_table('customer', con=con)
df = df.sample(frac=0.1)


from phd.bn import chow_liu


blacklist = [
    att for att in df.columns
    if '_id' in att or 'id_' in att or att == 'id' or '_sk' in att
]

tree = chow_liu.chow_liu_tree(df, blacklist)

bn = chow_liu.create_bn(df, tree)

print(type(bn))
