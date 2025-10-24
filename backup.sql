BEGIN TRANSACTION;
CREATE TABLE assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT, watch_count INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
INSERT INTO "assignments" VALUES(3,3,'MLF  End Term PYQ  | Jan 23 FN','https://youtu.be/4uUYBwIQMNg',2,0);
INSERT INTO "assignments" VALUES(4,3,'MLF  End Term PYQ  | May 23 FN','https://youtu.be/Bv4NA-TDdro',0,0);
INSERT INTO "assignments" VALUES(5,3,'MLF  End Term PYQ  | May 23 AN','https://youtu.be/oFShvOKqjxg',1,0);
INSERT INTO "assignments" VALUES(6,3,'MLF  End Term PYQ  | September 23 AN','https://youtu.be/QgxHiQQN4mU',1,0);
INSERT INTO "assignments" VALUES(7,3,'MLF  End Term PYQ  | Jan 24','https://youtu.be/8dj3sX5FYX8',1,0);
INSERT INTO "assignments" VALUES(8,3,'MLF  End Term PYQ  | May 24','https://youtu.be/KFx1nhlCSkg',2,0);
INSERT INTO "assignments" VALUES(9,3,'MLF  End Term PYQ  | September 24','https://youtu.be/YFejynQhdtY',3,0);
INSERT INTO "assignments" VALUES(10,3,'MLF  End Term PYQ  | Jan 25','',0,0);
INSERT INTO "assignments" VALUES(11,4,'MLT End Term PYQ | Jan 24','https://youtu.be/ucBQvcVu1II',4,0);
INSERT INTO "assignments" VALUES(12,5,'PDSA Week-9 PYQ','https://youtu.be/CR_GF9siGGc',1,0);
INSERT INTO "assignments" VALUES(13,5,'PDSA Week-11 PYQ','',0,0);
INSERT INTO "assignments" VALUES(14,5,'PDSA End Term PYQ | September 23 AN','https://youtu.be/q6cI-nvL9_w',2,0);
INSERT INTO "assignments" VALUES(15,5,'PDSA End Term PYQ | Jan 24 FN','https://youtu.be/bilgN4EdbLk',1,0);
INSERT INTO "assignments" VALUES(16,5,'PDSA OPPE PYQ Set-1','https://youtu.be/4AMkJ9mI-oI',0,0);
INSERT INTO "assignments" VALUES(17,5,'PDSA OPPE PYQ Set-2','https://youtu.be/U8jsBwhe3TI',0,0);
INSERT INTO "assignments" VALUES(18,9,'DBMS Week-9 One Shot Revision','https://youtu.be/easRDRwivTY',0,0);
INSERT INTO "assignments" VALUES(19,9,'DBMS Week-10 One Shot Revision Part-1','https://youtu.be/H2RFmItDEh0',0,0);
INSERT INTO "assignments" VALUES(20,9,'DBMS Week-10 One Shot Revision Part-2','https://youtu.be/XhQse4oZP-M',0,0);
INSERT INTO "assignments" VALUES(21,9,'DBMS Week-11 One Shot Revision ','https://youtu.be/oU8bDX5E0UQ',1,0);
INSERT INTO "assignments" VALUES(22,9,'DBMS Week-12 One Shot Revision Part-1','https://youtu.be/QHiqNebNP7s',0,0);
INSERT INTO "assignments" VALUES(23,9,'DBMS Week-12 One Shot Revision Part-2','https://youtu.be/Cy9LuqeBE1Y',0,0);
INSERT INTO "assignments" VALUES(25,1,'BA End Term RAPID REVISION','https://youtu.be/6Gdz9z_APAM',62,0);
INSERT INTO "assignments" VALUES(26,1,'BA End Term PYQ | May 24','https://youtu.be/B5FzpJKSMS0',38,0);
INSERT INTO "assignments" VALUES(27,1,'BA End Term PYQ | September 24','https://youtu.be/1ecukKO2r5g',31,0);
INSERT INTO "assignments" VALUES(28,15,'SC End Term PYQ | May 24','https://youtu.be/3xGSs4vmp4A?si=P1l0mfmdrxTkLmcV',0,0);
INSERT INTO "assignments" VALUES(29,15,'SC End Term PYQ | September 24','https://youtu.be/0MQ1fjaEqBo?si=G1fFGgFRaDHC1tRF',0,0);
INSERT INTO "assignments" VALUES(30,4,'MLT End Term PYQ | Jan 25','https://youtu.be/h_nU2QlSe2o',4,0);
INSERT INTO "assignments" VALUES(31,1,'BA End Term PYQ | Jan 25 FN','https://youtu.be/Tbqgy8Cv-cM',48,0);
INSERT INTO "assignments" VALUES(32,1,'BA End Term PYQ | Jan 25 AN','https://youtu.be/o8qoFVKy-yY',66,1);
INSERT INTO "assignments" VALUES(33,4,'MLT End Term PYQ | May 25','',0,1);
CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
INSERT INTO "courses" VALUES(1,'Business Analytics ');
INSERT INTO "courses" VALUES(3,'MLF');
INSERT INTO "courses" VALUES(4,'MLT');
INSERT INTO "courses" VALUES(5,'PDSA(Theory+OPPE)');
INSERT INTO "courses" VALUES(9,'DBMS (Theory+OPPE)');
INSERT INTO "courses" VALUES(13,'PYTHON (OPPE)');
INSERT INTO "courses" VALUES(14,'MLP (Developer Harsh)');
INSERT INTO "courses" VALUES(15,'system command(code synth)');
CREATE TABLE extra_stuff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            link TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
INSERT INTO "extra_stuff" VALUES(1,1,'Course Grade Calculator','https://ba-quiz-calculator.vercel.app/');
CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            feedback TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
