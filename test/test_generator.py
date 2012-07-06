#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import os
import sys
import logging
import unittest
import csv
import sqlite3 as sql

sys.path.append( '.' )
sys.path.append( '../lib/' )
from generator import *

"""
TODO: Add documentation as needed.
"""


class TestGenerator(unittest.TestCase):

    def setUp(self):
        # print "setup"
        pass 

    def test_process_csv(self):
        file_name = open("gen_sample.csv", "rb")
        csv_reader = process_csv(file_name)
        for i, row in enumerate(csv_reader):
            assert([str(i),"foo", "bar", "01234567"] == row)

    def test_build_query_string(self):
        test_first_name = "FOO"
        test_last_name = "BAR"
        test_patent_number = "D1234567"
        test_result = """SELECT * FROM invpat WHERE 
                        (Firstname = \"%s\" and Lastname = \"%s\"
                         and Patent = \"%s\");""" % (test_first_name, test_last_name, test_patent_number)
        assert(test_result == build_query_string(test_first_name, test_last_name, test_patent_number))

    def test_con_sql_match(self):
        query_string =  """SELECT Firstname, Lastname, Patent FROM TEST WHERE 
                        (Firstname = \"JOHN\" and Lastname = \"SMITH\"
                         and Patent = \"D01234567\");"""
        test_con = sql.connect('test_db')
        test_con_cur = test_con.cursor()  
        test_con_cur.execute(""" DROP TABLE IF EXISTS TEST; """)
        test_con_cur.execute(""" CREATE TABLE TEST(
                                 Firstname TEXT,
                                 Lastname TEXT,
                                 Patent TEXT); """)
        test_con_cur.execute(""" INSERT INTO TEST 
                                 VALUES("JOHN", "SMITH", "D01234567"); """)
        test_con.commit()
        match = con_sql_match(query_string, 'test_db')
        assert(match[0] == "JOHN") # Firstname
        assert(match[1] == "SMITH") # Lastname
        assert(match[2] == "D01234567") # Patent
        query_string_dne =  """SELECT Firstname, Lastname, Patent FROM TEST WHERE 
                        (Firstname = \"JOHN\" and Lastname = \"NULL\"
                         and Patent = \"D01234567\");"""
        match = con_sql_match(query_string_dne, 'test_db')
        assert(not match)
        
                                 
                                 
        
        
                          

if __name__ == '__main__':
    unittest.main()
