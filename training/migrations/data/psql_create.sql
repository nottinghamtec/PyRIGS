-- Exported from MS Access to PostgreSQL
-- (C) 1997-98 CYNERGI - www.cynergi.net, info@cynergi.net

CREATE TABLE Categories
     (
     ID                    serial,
     Category_Number      int8,
     Category_Name        varchar(255),
     PRIMARY KEY (ID)
     );


CREATE TABLE Members
     (
     ID                    serial,
     Member_Name          varchar(255),
     PRIMARY KEY (ID)
     );


CREATE TABLE tblrequirements
     (
     ID                    serial,
     level_id             int8,
     item_id              int8,
     PRIMARY KEY (ID)
     );


CREATE TABLE Training_Items
     (
     ID                    serial,
     Category_ID          int8     REFERENCES Categories,
     Item_Number          int8,
     Item_Name            varchar(255),
     PRIMARY KEY (ID)
     );


CREATE TABLE Training_Level_Records
     (
     ID                    serial,
     Member_ID            int8,
     Training_Level_ID    int8,
     Date_Level_Awarded   DATE,
     PRIMARY KEY (ID)
     );


CREATE TABLE Training_Levels
     (
     ID                    serial,
     Level_Name           varchar(255),
     PRIMARY KEY (ID)
     );


CREATE TABLE Training_Records
     (
     ID                    serial,
     Member_ID            int8     REFERENCES Members,
     Training_Item_ID     int8     REFERENCES Training_Items,
     Started_Date         DATE,
     Started_Assessor     int8     REFERENCES Members,
     Started_Notes        text,
     Complete_Date        DATE,
     Complete_Assessor    int8     REFERENCES Members,
     Complete_Notes       text,
     Assessed_Date        DATE,
     Assessed_Assessor    int8     REFERENCES Members,
     Assessed_Notes       text,
     PRIMARY KEY (ID)
     );

