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
CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT, watch_count INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
INSERT INTO "notes" VALUES(3,3,'MLF Quiz-2 PYQ  | Jan 2023','https://youtu.be/t0zDodn69fk',0,0);
INSERT INTO "notes" VALUES(4,3,'MLF Quiz-2 PYQ  | May 2023','https://youtu.be/1aFlukVN9vM',0,0);
INSERT INTO "notes" VALUES(5,3,'MLF Quiz-2 PYQ  | September 2023','https://youtu.be/vaj4TkwDGCI',0,0);
INSERT INTO "notes" VALUES(6,3,'MLF Quiz-2 PYQ  | Jan 24','https://youtu.be/jcDcIrN5ED0',0,0);
INSERT INTO "notes" VALUES(7,3,'MLF Quiz-2 MOCK','https://youtu.be/bBNR_eYIWFc',0,0);
INSERT INTO "notes" VALUES(8,3,'MLF Quiz-2 PYQ  | May 24','https://youtu.be/GJYTP0Bb_fw',0,0);
INSERT INTO "notes" VALUES(9,3,'MLF Quiz-2 PYQ  | September 24','https://youtu.be/ZTbZbdCvO3U',0,0);
INSERT INTO "notes" VALUES(10,3,'MLF  Quiz-2 PYQ | Jan 25','https://youtu.be/s8EdLumePe8',0,0);
INSERT INTO "notes" VALUES(11,4,'MLT QUIZ-2 MOCK','https://youtu.be/LXoNyBrrOAo',0,0);
INSERT INTO "notes" VALUES(12,4,'MLT Quiz-2 PYQ | Jan 24','https://youtu.be/PGXY0CwZeNQ',0,0);
INSERT INTO "notes" VALUES(13,4,'MLT Quiz-2 PYQ | May 24','https://youtu.be/NQgYjrFkXoo',0,0);
INSERT INTO "notes" VALUES(14,5,'PDSA Week-5 PYQ','https://youtu.be/TU8i3jICbZM',0,0);
INSERT INTO "notes" VALUES(15,5,'PDSA Week-6 PYQ','https://youtu.be/cNqMFB9Cm68',0,0);
INSERT INTO "notes" VALUES(16,5,'PDSA Week-7 PYQ','https://youtu.be/kJxAh7nYTak',0,0);
INSERT INTO "notes" VALUES(17,5,'PDSA Week-8 PYQ','https://youtu.be/CR_GF9siGGc',0,0);
INSERT INTO "notes" VALUES(18,5,'PDSA Quiz-2 PYQ | Jan 23','https://youtu.be/siGORn9MAug',0,0);
INSERT INTO "notes" VALUES(19,5,'PDSA Quiz-2 PYQ | September 23','https://youtu.be/QbewTYOpDTw',0,0);
INSERT INTO "notes" VALUES(20,9,'DBMS Week-5 One Shot Revision','https://youtu.be/MHN7HN8zQ28',0,0);
INSERT INTO "notes" VALUES(21,9,'DBMS Week-6 One Shot Revision','https://youtu.be/AG8w_J9vaTQ',0,0);
INSERT INTO "notes" VALUES(22,9,'DBMS Week-8 One Shot Revision Part-1','https://youtu.be/AG8w_J9vaTQ',0,0);
INSERT INTO "notes" VALUES(23,9,'DBMS Week-8 One Shot Revision Part-2','https://youtu.be/-MiPacTEjTE',0,0);
INSERT INTO "notes" VALUES(25,1,'BA Week-5 Theory + PA','https://youtu.be/mjUw3nbnpRw',17,0);
INSERT INTO "notes" VALUES(26,1,'BA Week-5 Question ','https://youtu.be/vNfRMq54SfQ',13,0);
INSERT INTO "notes" VALUES(27,1,'BA Week-6 Theory + PA','https://youtu.be/jrO48GOnPrU',11,0);
INSERT INTO "notes" VALUES(28,1,'BA Week-7 Theory + PA','https://youtu.be/8NpqqJzJBXg',10,0);
INSERT INTO "notes" VALUES(29,1,'BA Week-8,9 Theory + Question ','https://youtu.be/AHzUPdMlM9I',18,0);
INSERT INTO "notes" VALUES(30,1,'BA Week-5 MOCK','',0,0);
INSERT INTO "notes" VALUES(31,1,'BA Week-6 MOCK','',0,0);
INSERT INTO "notes" VALUES(32,1,'BA Week-7 MOCK','',0,0);
INSERT INTO "notes" VALUES(33,1,'BA Quiz-2 PYQ | May 24','https://youtu.be/YsWyz6k13O8',2,0);
INSERT INTO "notes" VALUES(34,1,'BA Quiz-2 PYQ | September 24','https://youtu.be/QxvSQWRg2bY',2,0);
INSERT INTO "notes" VALUES(35,15,'SC Week-5 Theory + Practical','https://youtu.be/s3pR7yoxwDs?si=KfbbQLgUz2sJAnzH',0,0);
INSERT INTO "notes" VALUES(36,15,'SC Week-6 Theory + Practical','https://youtu.be/hPqXZhKgeqw?si=_cPS_UE3qTQZQgVs',0,0);
INSERT INTO "notes" VALUES(37,4,'MLT Quiz-2 PYQ | Jan 25','https://youtu.be/XmoJQaW_f-Q',0,0);
INSERT INTO "notes" VALUES(38,1,'BA Quiz-2 PYQ | Jan 25','https://youtu.be/FTgKDEWeSaI',2,0);
INSERT INTO "notes" VALUES(39,1,'BA Quiz-2 PYQ | May 25','https://youtu.be/c0tAahlH8Nw',6,0);
CREATE TABLE pyqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT, watch_count INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
INSERT INTO "pyqs" VALUES(2,1,'Course Intro Video','https://youtu.be/VT9ToOPawW0',10,0);
INSERT INTO "pyqs" VALUES(3,1,'Week-1 Theory + PA + Question','https://youtu.be/tnInGENQaVc',14,0);
INSERT INTO "pyqs" VALUES(4,1,'Week-2 Theory + PA + Question','https://youtu.be/ng7H0pz0ec0',12,0);
INSERT INTO "pyqs" VALUES(7,3,'MLF Week-2 Activity Question','https://youtu.be/8xPykL8_miI?si=ffcXp7gqzOQCzt5e',1,0);
INSERT INTO "pyqs" VALUES(8,9,'DBMS Week-1 One Shot Revision','https://youtu.be/xQfSvRzJOQ4',0,0);
INSERT INTO "pyqs" VALUES(9,9,'DBMS Week-2 One Shot Revision','https://youtu.be/8gCgg0KrRT8',0,0);
INSERT INTO "pyqs" VALUES(10,3,'MLF Week-3 Activity Question','https://youtu.be/5iRjPm39TR0',0,0);
INSERT INTO "pyqs" VALUES(11,3,'MLF Week-4 Activity Question','https://youtu.be/o9Ifuw-NmaA',0,0);
INSERT INTO "pyqs" VALUES(12,3,'MLF  Quiz-1 PYQ | September 23','https://youtu.be/ApaNZzRQZMY',0,0);
INSERT INTO "pyqs" VALUES(13,3,'MLF  Quiz-1 PYQ | Jan 24','https://youtu.be/93bOUjx-bJo',0,0);
INSERT INTO "pyqs" VALUES(14,3,'MLF  Quiz-1 PYQ | May 24','https://youtu.be/NNbusI2kv-4',0,0);
INSERT INTO "pyqs" VALUES(15,3,'MLF  Quiz-1 PYQ | September 24','https://youtu.be/FpMJ5I948pI',0,0);
INSERT INTO "pyqs" VALUES(16,3,'MLF  Quiz-1 PYQ | Jan 25','',0,0);
INSERT INTO "pyqs" VALUES(17,4,'MLT Week-1 Activity Question','https://youtu.be/LD3FhSg9Shk',1,0);
INSERT INTO "pyqs" VALUES(18,4,'MLT Week-2 Activity Question','https://youtu.be/tmdC-E58x9w',0,0);
INSERT INTO "pyqs" VALUES(19,4,'MLT Week-3 Activity Question','https://youtu.be/_LUB8dQxMMU',0,0);
INSERT INTO "pyqs" VALUES(20,4,'MLT QUIZ-1 MOCK','https://youtu.be/pe8AtHjR6w4',0,0);
INSERT INTO "pyqs" VALUES(21,4,'MLT Quiz-1 PYQ | May 23','https://youtu.be/ZAIl_SHFEhI',0,0);
INSERT INTO "pyqs" VALUES(22,4,'MLT Quiz-1 PYQ | September 23','https://youtu.be/9wkVlD6pWQs',0,0);
INSERT INTO "pyqs" VALUES(23,4,'MLT Quiz-1 PYQ | Jan 24','https://youtu.be/n_ulXMBwNhU',0,0);
INSERT INTO "pyqs" VALUES(24,4,'MLT Quiz-1 PYQ | September 24','https://youtu.be/G07lrcEo5T8',0,0);
INSERT INTO "pyqs" VALUES(26,5,'PDSA Week-2 PYQ','https://youtu.be/7E4yPHHyOYA',0,0);
INSERT INTO "pyqs" VALUES(27,5,'PDSA Week-3 PYQ','https://youtu.be/4iNU_E2_y9k',0,0);
INSERT INTO "pyqs" VALUES(28,5,'PDSA Week-4 PYQ','https://youtu.be/V2RZ8PY37Ts',0,0);
INSERT INTO "pyqs" VALUES(29,5,'PDSA Quiz-1 PYQ | Jan 24','https://youtu.be/FNfmEJqK8bU',0,0);
INSERT INTO "pyqs" VALUES(30,5,'PDSA Quiz-1 PYQ | May 24','https://youtu.be/MGchbfQqXt4',0,0);
INSERT INTO "pyqs" VALUES(32,9,'DBMS OPPE PYQ PlayList','https://www.youtube.com/playlist?list=PLTewhG5vbW7EKmyl32LAzSJLcEtuK1fer',1,0);
INSERT INTO "pyqs" VALUES(33,9,'DBMS OPPE PYQ PlayList ( Developer Harsh)','https://youtube.com/playlist?list=PLDfna1ApN44qNuRotBr2ahcs9Khvesw3O&si=KPmpMeTun4dN1-1L',0,0);
INSERT INTO "pyqs" VALUES(34,1,'BA Week-3 Theory','https://youtu.be/FJRSeQ80B1M',9,0);
INSERT INTO "pyqs" VALUES(35,1,'BA Week-3 PA + Question','https://youtu.be/kGuzZ6M3sc4',4,0);
INSERT INTO "pyqs" VALUES(36,1,'BA Week-4 Theory','https://youtu.be/7cqiKctIAQ0',4,0);
INSERT INTO "pyqs" VALUES(39,1,'BA Week-4 MOCK','',0,0);
INSERT INTO "pyqs" VALUES(40,1,'BA Quiz-1 PYQ | May 24','https://youtu.be/j6olYcxJDHk',0,0);
INSERT INTO "pyqs" VALUES(41,1,'BA Quiz-1 PYQ | September 24','https://youtu.be/fLfVT2CaMDU',0,0);
INSERT INTO "pyqs" VALUES(42,13,'PYTHON OPPE PYQ Playlist','https://www.youtube.com/playlist?list=PLTewhG5vbW7E1vbVy22w5gSkQirEEYgLC',1,0);
INSERT INTO "pyqs" VALUES(43,14,'Pandas Fundamentals','https://youtu.be/0lMo3IwyTDE?si=u0f2e1xT7KagUxAo',1,0);
INSERT INTO "pyqs" VALUES(44,14,'Pandas Data Exploration','https://youtu.be/GxeMevMQAbY?si=uLACmG5-WBkaIMRG',0,0);
INSERT INTO "pyqs" VALUES(45,14,'Basic Data Selection using pandas','https://youtu.be/RV0JuTDeO88?si=DtMvArjP_ngCgDl0',1,0);
INSERT INTO "pyqs" VALUES(46,14,'Intermediate Data Selection Techniques in Pandas','https://youtu.be/IdFgZiord-o?si=RdbHZjxWdhoC8kI_',0,0);
INSERT INTO "pyqs" VALUES(47,14,'Data Manipulation using Pandas (Part 1) ','https://youtu.be/53MbqRKSfAQ?si=yYw4PQ-8aAv-PD7E',2,0);
INSERT INTO "pyqs" VALUES(48,14,'Data Manipulation using Pandas (Part 2)','https://youtu.be/LqPM_zR-iR4?si=n82P_Ccf5-yh-Q9m',0,0);
INSERT INTO "pyqs" VALUES(49,15,'SC Week-1 Theory','https://youtu.be/kt7NWWknt7g?si=WKKZcMYrUD4QdsLm',0,0);
INSERT INTO "pyqs" VALUES(50,15,'SC Week-1 Practical','https://youtu.be/BN58MIsNoNI?si=qqc01rqsC9p35rZj',0,0);
INSERT INTO "pyqs" VALUES(51,15,'SC Week-2 Theory + Practical','https://youtu.be/R4fg5N4A4v8?si=ot9lSj8vp-DChMv4',0,0);
INSERT INTO "pyqs" VALUES(52,15,'SC Week-3 Theory + Practical','https://youtu.be/I5iNrwYY3-g?si=dFPpGF2P2nSdxtbt',0,0);
INSERT INTO "pyqs" VALUES(53,15,'SC Week-4 Theory + Practical','https://youtu.be/exn3eq440Zs?si=1f-FNTDpK9SF9OwD',0,0);
INSERT INTO "pyqs" VALUES(54,15,'SC Quiz-1 PYQ | May 24','https://youtu.be/oEwtzNOJcSg?si=nf2WPMQKsws7qDrU',0,0);
INSERT INTO "pyqs" VALUES(55,15,'SC Quiz-1 PYQ | September 24','https://youtu.be/iliZN4uthCg?si=q6ArDByGdk-yRWzf',0,0);
INSERT INTO "pyqs" VALUES(56,1,'BA Quiz-1 PYQ | January 25','https://youtu.be/NL-30EDLJj0',1,0);
CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            yt_link TEXT,
            watch_count INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
INSERT INTO "resources" VALUES(1,1,'ALL ANOVA QUESTION HERE','https://docs.google.com/document/d/1H2GT0n6huAr9H7hdGzDhQlUWAPuiUQv7e3xP9hwbqEs/edit?usp=sharing',63,0);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('courses',16);
INSERT INTO "sqlite_sequence" VALUES('pyqs',56);
INSERT INTO "sqlite_sequence" VALUES('notes',39);
INSERT INTO "sqlite_sequence" VALUES('assignments',32);
INSERT INTO "sqlite_sequence" VALUES('extra_stuff',1);
INSERT INTO "sqlite_sequence" VALUES('resources',1);
INSERT INTO "sqlite_sequence" VALUES('feedback',1);
COMMIT;
