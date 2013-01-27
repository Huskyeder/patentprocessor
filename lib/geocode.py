#Non_US http://earth-info.nga.mil/gns/html/gis_countryfiles.htm
#US     http://geonames.usgs.gov/domestic/download_data.htm

##NEED TO DO...
##    CREATE INDEX IF NOT EXISTS idx_ctc0 ON gnsloc (SORT_NAME, CC1);

import datetime, csv, os, re, sqlite3

#from fwork import *
# We need to import these one at a time because many of these functions are
# duplicated in multiple places. That is, there are 3 or 4 identical or
# slightly different versions located in different files.

from fwork import jarow
from fwork import cityctry
from fwork import tblExist

# geocode_replace_loc consists of a series of functions,
# each with a SQL statement that is passed as a parameter
# to replace_loc. Uses temporary tables for handling 
# intermediate relations.
from geocode_replace_loc import *

# TODO: switch to import the tested version of sep_wrd.
# from sep_wrd_geocode import sep_wrd

def sep_wrd(word, seq):
    if seq==-1:
        return word
    else:
        p = re.compile(" *?[,|] *")
        ln = p.split(word)
        if len(ln)> seq:
            return ln[seq]
        else:
            return ""

conn = sqlite3.connect("hashTbl.sqlite3")
c = conn.cursor()

# TODO: Consider replacing the lambdas with functions which can be tested.

conn.create_function("blk_split", 1, lambda x: re.sub(" ", "", x))
conn.create_function("sep_cnt",   1, lambda x: len(re.findall("[,|]", x)))
conn.create_function("jarow",     2, jarow)
conn.create_function("cityctry",  3, cityctry)
conn.create_function("sep_wrd",   2, sep_wrd)
conn.create_function("rev_wrd",   2, lambda x,y:x.upper()[::-1][:y])

# Now set up the databases necessary for the geocoding to proceed.

# NOTE: Keep these imports function-specific until everything
# is covered with unit tests, and we know that the structure
# is maintainable.

from geocode_setup import geocode_db_initialize
from geocode_setup import loc_create_table
from geocode_setup import fix_city_country
from geocode_setup import fix_state_zip
from geocode_setup import create_loc_indexes
from geocode_setup import create_usloc_table
from geocode_setup import create_locMerge_table

geocode_db_initialize(c)
loc_create_table(c)

print datetime.datetime.now()

if not(tblExist(c, "locMerge")):
    fix_city_country(c)
    fix_state_zip(c)
    create_loc_indexes(conn)

create_usloc_table(c)
create_locMerge_table(c)

print datetime.datetime.now()


# This should be the end of the setup, and all the above should be able
# to go into its own file and be imported into this script. One benefit
# of separating it out may be to allow much easier unit testing for the
# location matching which follows.


# TODO: Find a way to unit test this set of queries
def create_loc_and_locmerge_tables(conn):
    conn.executescript("""

        CREATE TEMPORARY TABLE temp2 AS
            SELECT  CityA,
                    StateA,
                    CountryA,
                    ZipcodeA,
                    count(*) as cnt
              FROM  temp1
          GROUP BY  CityA,
                    StateA,
                    CountryA,
                    ZipcodeA;

        CREATE INDEX IF NOT EXISTS t1_idx ON temp1 (CityA, StateA, CountryA, ZipcodeA);
        CREATE INDEX IF NOT EXISTS t2_idx ON temp2 (CityA, StateA, CountryA, ZipcodeA);

        INSERT OR REPLACE INTO locMerge
            SELECT  b.cnt,
                    a.*,
                    SUBSTR(a.CityA,1,3)
              FROM  temp1 AS a
        INNER JOIN  temp2 AS b
                ON  a.CityA = b.CityA
               AND  a.StateA = b.StateA
               AND  a.CountryA = b.CountryA
               AND  a.ZipcodeA = b.ZipcodeA;

        CREATE TEMPORARY TABLE temp3 AS
            SELECT  a.*
              FROM  LOC AS a
              LEFT JOIN locMerge AS b
                ON  a.City = b.City
               AND  a.State = b.State
               AND  a.Country = b.Country
               AND  a.Zipcode = b.Zipcode
             WHERE  b.Zipcode IS NULL;

        DROP TABLE IF EXISTS loc;

        CREATE TABLE loc AS SELECT * FROM temp3;

        CREATE INDEX IF NOT EXISTS loc_idxCC ON loc (City, Country);
        CREATE INDEX IF NOT EXISTS loc_idx   ON loc (City, State, Country, Zipcode);
        CREATE INDEX IF NOT EXISTS loc_idxCS ON loc (City, State);

        DROP TABLE IF EXISTS temp2;
        DROP TABLE IF EXISTS temp3;
          """)



# TODO: Unit test this so that it and the unit test can be
# eliminated in a future redesign. Also, ensure that this
# is the correct name for this function, and adjust accordingly.
def table_temp1_has_rows(conn):
    return conn.execute("SELECT count(*) FROM temp1").fetchone()[0] > 0


# TODO: Unit test extensively.
def replace_loc(script):

    stmt_to_execute = """
       DROP TABLE IF EXISTS temp1;
       CREATE TEMPORARY TABLE temp1 AS %s;
       CREATE INDEX IF NOT EXISTS tmp1_idx ON temp1 (CityA, StateA, CountryA, ZipcodeA);
       """ % script
    c.executescript(stmt_to_execute)

    # TODO: Refactor into its own function, unit test.
    # Also, consider deleting, as these do not appear to be
    # used anywhere in the code.
    field = ["[%s]" % x[1] for x in c.execute("PRAGMA TABLE_INFO(temp1)")][2:6]
    var_f = ",".join(field)

    # TODO: Refactor into at least two functions. Main refactor is
    # Handling the body of the if block (DONE). The second refactor is
    # handling the conditional expression for the if block (DONE).
    #if c.execute("SELECT count(*) FROM temp1").fetchone()[0]>0:
    # Which tables will pass this conditional?
    if table_temp1_has_rows(c):
        create_loc_and_locmerge_tables(c)
        VarX = c.execute("select count(*) from loc").fetchone()[0]
        VarY = c.execute("select count(*) from locMerge").fetchone()[0]
        print " - Loc =", VarX, " OkM =", VarY, " Total =", VarX+VarY, "  ", datetime.datetime.now()

    conn.commit()

# Prefixed tablename (loc) with with dbname (also loc)
print "Loc =", c.execute("select count(*) from loc.loc").fetchone()[0]

# TODO: Refactor the range call into it's own function, unit test
# that function extensively.
# TODO: Figure out what these hardcoded parameters mean.
for scnt in range(-1, c.execute("select max(sep_cnt(city)) from loc.loc").fetchone()[0]+1):

    sep = scnt
    print "------", scnt, "------"
    replace_loc(domestic_sql()                            % (sep, scnt))
    replace_loc(domestic_block_remove_sql()               % (sep, scnt))
    replace_loc(domestic_first3_jaro_winkler_sql()        % (sep, sep, "10.92", scnt))
    replace_loc(domestic_last4_jaro_winkler_sql()         % (sep, sep, "10.90", scnt))
    replace_loc(foreign_country_full_name_1_sql()         % (sep, scnt))
    replace_loc(foreign_country_full_name_2_sql()         % (sep, scnt))
    replace_loc(foreign_country_short_form_sql()          % (sep, scnt))
    replace_loc(foreign_country_block_split_sql()         % (sep, scnt))
    replace_loc(foreign_country_first3_jaro_winkler_sql() % (sep, sep, "20.92", scnt))
    replace_loc(foreign_country_last4_jaro_winkler_sql()  % (sep, sep, "20.90", scnt))

### End of for loop

print "------ F ------"

replace_loc(domestic_2nd_layer_sql())
replace_loc(domestic_first3_2nd_jaro_winkler_sql()        % ("14.95"))
replace_loc(foreign_full_name_2nd_layer_sql())
replace_loc(foreign_full_nd_2nd_layer_sql())
replace_loc(foreign_no_space_2nd_layer_sql())
replace_loc(foreign_country_first3_2nd_jaro_winkler_sql() % ("24.95"))
replace_loc(domestic_zipcode_sql())

conn.commit()
c.close()
conn.close()
