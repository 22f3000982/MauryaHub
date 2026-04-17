-- Database backup created at 2025-12-19T02:53:25.729894

-- Backup for table courses
DELETE FROM courses;
INSERT INTO courses (id, name) VALUES (1, 'Business Analytics ');
INSERT INTO courses (id, name) VALUES (3, 'MLF');
INSERT INTO courses (id, name) VALUES (4, 'MLT');
INSERT INTO courses (id, name) VALUES (5, 'PDSA(Theory+OPPE)');
INSERT INTO courses (id, name) VALUES (9, 'DBMS (Theory+OPPE)');
INSERT INTO courses (id, name) VALUES (13, 'PYTHON (OPPE)');
INSERT INTO courses (id, name) VALUES (14, 'MLP (Developer Harsh)');
INSERT INTO courses (id, name) VALUES (15, 'system command(code synth)');

-- Backup for table quiz1
DELETE FROM quiz1;
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (16, 3, 'MLF  Quiz-1 PYQ | Jan 25', '', 0, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (39, 1, 'BA Week-4 MOCK', '', 0, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (23, 4, 'MLT Quiz-1 PYQ | Jan 24', 'https://youtu.be/n_ulXMBwNhU', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (2, 1, 'Course Intro Video', 'https://youtu.be/VT9ToOPawW0', 15, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (36, 1, 'BA Week-4 Theory', 'https://youtu.be/7cqiKctIAQ0', 11, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (53, 15, 'SC Week-4 Theory + Practical', 'https://youtu.be/exn3eq440Zs?si=1f-FNTDpK9SF9OwD', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (1, 1, 'BA Quiz-1 PYQ | September 25', '', 0, 2);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (15, 3, 'MLF  Quiz-1 PYQ | September 24', 'https://youtu.be/FpMJ5I948pI', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (41, 1, 'BA Quiz-1 PYQ | September 24', 'https://youtu.be/fLfVT2CaMDU', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (35, 1, 'BA Week-3 PA + Question', 'https://youtu.be/kGuzZ6M3sc4', 11, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (12, 3, 'MLF  Quiz-1 PYQ | September 23', 'https://youtu.be/ApaNZzRQZMY', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (11, 3, 'MLF Week-4 Activity Question', 'https://youtu.be/o9Ifuw-NmaA', 2, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (26, 5, 'PDSA Week-2 PYQ', 'https://youtu.be/7E4yPHHyOYA', 6, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (58, 4, 'MLT Quiz-1 PYQ | MAY 25', 'https://youtu.be/iqnhPo7Le4U', 4, 1);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (18, 4, 'MLT Week-2 Activity Question', 'https://youtu.be/tmdC-E58x9w', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (54, 15, 'SC Quiz-1 PYQ | May 24', 'https://youtu.be/oEwtzNOJcSg?si=nf2WPMQKsws7qDrU', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (42, 13, 'PYTHON OPPE PYQ Playlist', 'https://www.youtube.com/playlist?list=PLTewhG5vbW7E1vbVy22w5gSkQirEEYgLC', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (24, 4, 'MLT Quiz-1 PYQ | September 24', 'https://youtu.be/G07lrcEo5T8', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (47, 14, 'Data Manipulation using Pandas (Part 1) ', 'https://youtu.be/53MbqRKSfAQ?si=yYw4PQ-8aAv-PD7E', 3, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (17, 4, 'MLT Week-1 Activity Question', 'https://youtu.be/LD3FhSg9Shk', 12, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (19, 4, 'MLT Week-3 Activity Question', 'https://youtu.be/_LUB8dQxMMU', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (55, 15, 'SC Quiz-1 PYQ | September 24', 'https://youtu.be/iliZN4uthCg?si=q6ArDByGdk-yRWzf', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (7, 3, 'MLF Week-2 Activity Question', 'https://youtu.be/8xPykL8_miI?si=ffcXp7gqzOQCzt5e', 5, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (3, 1, 'Week-1 Theory + PA + Question', 'https://youtu.be/tnInGENQaVc', 21, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (34, 1, 'BA Week-3 Theory', 'https://youtu.be/FJRSeQ80B1M', 17, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (20, 4, 'MLT QUIZ-1 MOCK', 'https://youtu.be/pe8AtHjR6w4', 3, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (57, 1, 'BA Quiz-1 PYQ | May 25', 'https://youtu.be/gyE82bQxnsg', 2, 1);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (14, 3, 'MLF  Quiz-1 PYQ | May 24', 'https://youtu.be/NNbusI2kv-4', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (51, 15, 'SC Week-2 Theory + Practical', 'https://youtu.be/R4fg5N4A4v8?si=ot9lSj8vp-DChMv4', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (8, 9, 'DBMS Week-1 One Shot Revision', 'https://youtu.be/xQfSvRzJOQ4', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (43, 14, 'Pandas Fundamentals', 'https://youtu.be/0lMo3IwyTDE?si=u0f2e1xT7KagUxAo', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (10, 3, 'MLF Week-3 Activity Question', 'https://youtu.be/5iRjPm39TR0', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (52, 15, 'SC Week-3 Theory + Practical', 'https://youtu.be/I5iNrwYY3-g?si=dFPpGF2P2nSdxtbt', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (46, 14, 'Intermediate Data Selection Techniques in Pandas', 'https://youtu.be/IdFgZiord-o?si=RdbHZjxWdhoC8kI_', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (32, 9, 'DBMS OPPE PYQ PlayList', 'https://www.youtube.com/playlist?list=PLTewhG5vbW7EKmyl32LAzSJLcEtuK1fer', 3, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (50, 15, 'SC Week-1 Practical', 'https://youtu.be/BN58MIsNoNI?si=qqc01rqsC9p35rZj', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (44, 14, 'Pandas Data Exploration', 'https://youtu.be/GxeMevMQAbY?si=uLACmG5-WBkaIMRG', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (29, 5, 'PDSA Quiz-1 PYQ | Jan 24', 'https://youtu.be/FNfmEJqK8bU', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (13, 3, 'MLF  Quiz-1 PYQ | Jan 24', 'https://youtu.be/93bOUjx-bJo', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (45, 14, 'Basic Data Selection using pandas', 'https://youtu.be/RV0JuTDeO88?si=DtMvArjP_ngCgDl0', 2, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (30, 5, 'PDSA Quiz-1 PYQ | May 24', 'https://youtu.be/MGchbfQqXt4', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (48, 14, 'Data Manipulation using Pandas (Part 2)', 'https://youtu.be/LqPM_zR-iR4?si=n82P_Ccf5-yh-Q9m', 1, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (49, 15, 'SC Week-1 Theory', 'https://youtu.be/kt7NWWknt7g?si=WKKZcMYrUD4QdsLm', 3, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (56, 1, 'BA Quiz-1 PYQ | January 25', 'https://youtu.be/NL-30EDLJj0', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (21, 4, 'MLT Quiz-1 PYQ | May 23', 'https://youtu.be/ZAIl_SHFEhI', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (40, 1, 'BA Quiz-1 PYQ | May 24', 'https://youtu.be/j6olYcxJDHk', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (22, 4, 'MLT Quiz-1 PYQ | September 23', 'https://youtu.be/9wkVlD6pWQs', 4, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (9, 9, 'DBMS Week-2 One Shot Revision', 'https://youtu.be/8gCgg0KrRT8', 2, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (33, 9, 'DBMS OPPE PYQ PlayList ( Developer Harsh)', 'https://youtube.com/playlist?list=PLDfna1ApN44qNuRotBr2ahcs9Khvesw3O&si=KPmpMeTun4dN1-1L', 3, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (28, 5, 'PDSA Week-4 PYQ', 'https://youtu.be/V2RZ8PY37Ts', 2, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (27, 5, 'PDSA Week-3 PYQ', 'https://youtu.be/4iNU_E2_y9k', 2, 0);
INSERT INTO quiz1 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (4, 1, 'Week-2 Theory + PA + Question', 'https://youtu.be/ng7H0pz0ec0', 17, 0);

-- Backup for table quiz2
DELETE FROM quiz2;
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (30, 1, 'BA Week-5 MOCK', '', 0, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (31, 1, 'BA Week-6 MOCK', '', 0, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (32, 1, 'BA Week-7 MOCK', '', 0, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (33, 1, 'BA Quiz-2 PYQ | May 24', 'https://youtu.be/YsWyz6k13O8', 17, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (26, 1, 'BA Week-5 Question ', 'https://youtu.be/vNfRMq54SfQ', 28, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (28, 1, 'BA Week-7 Theory + PA', 'https://youtu.be/8NpqqJzJBXg', 26, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (29, 1, 'BA Week-8,9 Theory + Question ', 'https://youtu.be/AHzUPdMlM9I', 39, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (9, 3, 'MLF Quiz-2 PYQ  | September 24', 'https://youtu.be/ZTbZbdCvO3U', 4, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (27, 1, 'BA Week-6 Theory + PA', 'https://youtu.be/jrO48GOnPrU', 25, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (14, 5, 'PDSA Week-5 PYQ', 'https://youtu.be/TU8i3jICbZM', 6, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (37, 4, 'MLT Quiz-2 PYQ | Jan 25', 'https://youtu.be/XmoJQaW_f-Q', 25, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (10, 3, 'MLF  Quiz-2 PYQ | Jan 25', 'https://youtu.be/s8EdLumePe8', 8, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (5, 3, 'MLF Quiz-2 PYQ  | September 2023', 'https://youtu.be/vaj4TkwDGCI', 2, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (7, 3, 'MLF Quiz-2 MOCK', 'https://youtu.be/bBNR_eYIWFc', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (36, 15, 'SC Week-6 Theory + Practical', 'https://youtu.be/hPqXZhKgeqw?si=_cPS_UE3qTQZQgVs', 1, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (8, 3, 'MLF Quiz-2 PYQ  | May 24', 'https://youtu.be/GJYTP0Bb_fw', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (22, 9, 'DBMS Week-8 One Shot Revision Part-1', 'https://youtu.be/AG8w_J9vaTQ', 1, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (34, 1, 'BA Quiz-2 PYQ | September 24', 'https://youtu.be/QxvSQWRg2bY', 20, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (20, 9, 'DBMS Week-5 One Shot Revision', 'https://youtu.be/MHN7HN8zQ28', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (16, 5, 'PDSA Week-7 PYQ', 'https://youtu.be/kJxAh7nYTak', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (17, 5, 'PDSA Week-8 PYQ', 'https://youtu.be/CR_GF9siGGc', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (3, 3, 'MLF Quiz-2 PYQ  | Jan 2023', 'https://youtu.be/t0zDodn69fk', 2, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (39, 1, 'BA Quiz-2 PYQ | May 25', 'https://youtu.be/c0tAahlH8Nw', 34, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (11, 4, 'MLT QUIZ-2 MOCK', 'https://youtu.be/LXoNyBrrOAo', 20, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (23, 9, 'DBMS Week-8 One Shot Revision Part-2', 'https://youtu.be/-MiPacTEjTE', 1, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (6, 3, 'MLF Quiz-2 PYQ  | Jan 24', 'https://youtu.be/jcDcIrN5ED0', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (21, 9, 'DBMS Week-6 One Shot Revision', 'https://youtu.be/AG8w_J9vaTQ', 1, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (12, 4, 'MLT Quiz-2 PYQ | Jan 24', 'https://youtu.be/PGXY0CwZeNQ', 14, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (4, 3, 'MLF Quiz-2 PYQ  | May 2023', 'https://youtu.be/1aFlukVN9vM', 12, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (19, 5, 'PDSA Quiz-2 PYQ | September 23', 'https://youtu.be/QbewTYOpDTw', 1, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (40, 4, 'MLT Quiz-2 PYQ | May 25', 'https://youtu.be/ZhlZUk2vLvI', 26, 1);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (38, 1, 'BA Quiz-2 PYQ | Jan 25', 'https://youtu.be/FTgKDEWeSaI', 21, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (15, 5, 'PDSA Week-6 PYQ', 'https://youtu.be/cNqMFB9Cm68', 2, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (25, 1, 'BA Week-5 Theory + PA', 'https://youtu.be/mjUw3nbnpRw', 34, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (18, 5, 'PDSA Quiz-2 PYQ | Jan 23', 'https://youtu.be/siGORn9MAug', 3, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (35, 15, 'SC Week-5 Theory + Practical', 'https://youtu.be/s3pR7yoxwDs?si=KfbbQLgUz2sJAnzH', 2, 0);
INSERT INTO quiz2 (id, course_id, name, yt_link, watch_count, sort_order) VALUES (13, 4, 'MLT Quiz-2 PYQ | May 24', 'https://youtu.be/NQgYjrFkXoo', 18, 0);

-- Backup for table endterm
DELETE FROM endterm;
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (10, 3, 'MLF  End Term PYQ  | Jan 25', '', 0, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (13, 5, 'PDSA Week-11 PYQ', '', 0, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (27, 1, 'BA End Term PYQ | September 24', 'https://youtu.be/1ecukKO2r5g', 39, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (33, 4, 'MLT End Term PYQ | May 25', 'https://youtu.be/1cP3xKGTSL4', 2, 1);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (11, 4, 'MLT End Term PYQ | Jan 24', 'https://youtu.be/ucBQvcVu1II', 11, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (31, 1, 'BA End Term PYQ | Jan 25 FN', 'https://youtu.be/Tbqgy8Cv-cM', 62, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (32, 1, 'BA End Term PYQ | Jan 25 AN', 'https://youtu.be/o8qoFVKy-yY', 80, 1);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (30, 4, 'MLT End Term PYQ | Jan 25', 'https://youtu.be/h_nU2QlSe2o', 14, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (26, 1, 'BA End Term PYQ | May 24', 'https://youtu.be/B5FzpJKSMS0', 49, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (15, 5, 'PDSA End Term PYQ | Jan 24 FN', 'https://youtu.be/bilgN4EdbLk', 5, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (14, 5, 'PDSA End Term PYQ | September 23 AN', 'https://youtu.be/q6cI-nvL9_w', 4, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (12, 5, 'PDSA Week-9 PYQ', 'https://youtu.be/CR_GF9siGGc', 4, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (22, 9, 'DBMS Week-12 One Shot Revision Part-1', 'https://youtu.be/QHiqNebNP7s', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (29, 15, 'SC End Term PYQ | September 24', 'https://youtu.be/0MQ1fjaEqBo?si=G1fFGgFRaDHC1tRF', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (20, 9, 'DBMS Week-10 One Shot Revision Part-2', 'https://youtu.be/XhQse4oZP-M', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (23, 9, 'DBMS Week-12 One Shot Revision Part-2', 'https://youtu.be/Cy9LuqeBE1Y', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (21, 9, 'DBMS Week-11 One Shot Revision ', 'https://youtu.be/oU8bDX5E0UQ', 2, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (16, 5, 'PDSA OPPE PYQ Set-1', 'https://youtu.be/4AMkJ9mI-oI', 11, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (17, 5, 'PDSA OPPE PYQ Set-2', 'https://youtu.be/U8jsBwhe3TI', 8, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (28, 15, 'SC End Term PYQ | May 24', 'https://youtu.be/3xGSs4vmp4A?si=P1l0mfmdrxTkLmcV', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (19, 9, 'DBMS Week-10 One Shot Revision Part-1', 'https://youtu.be/H2RFmItDEh0', 1, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (3, 3, 'MLF  End Term PYQ  | Jan 23 FN', 'https://youtu.be/4uUYBwIQMNg', 5, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (4, 3, 'MLF  End Term PYQ  | May 23 FN', 'https://youtu.be/Bv4NA-TDdro', 2, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (5, 3, 'MLF  End Term PYQ  | May 23 AN', 'https://youtu.be/oFShvOKqjxg', 3, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (18, 9, 'DBMS Week-9 One Shot Revision', 'https://youtu.be/easRDRwivTY', 3, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (9, 3, 'MLF  End Term PYQ  | September 24', 'https://youtu.be/YFejynQhdtY', 5, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (8, 3, 'MLF  End Term PYQ  | May 24', 'https://youtu.be/KFx1nhlCSkg', 4, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (6, 3, 'MLF  End Term PYQ  | September 23 AN', 'https://youtu.be/QgxHiQQN4mU', 3, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (25, 1, 'BA End Term RAPID REVISION', 'https://youtu.be/6Gdz9z_APAM', 71, 0);
INSERT INTO endterm (id, course_id, name, yt_link, watch_count, sort_order) VALUES (7, 3, 'MLF  End Term PYQ  | Jan 24', 'https://youtu.be/8dj3sX5FYX8', 3, 0);

-- Backup for table resources
DELETE FROM resources;
INSERT INTO resources (id, course_id, name, yt_link, watch_count, sort_order) VALUES (4, 1, 'BA Helper GPT', 'https://chatgpt.com/g/g-686e96fdf40c819181ea95b53e35cd4b-iitm-business-analytics-helper', 27, 2);
INSERT INTO resources (id, course_id, name, yt_link, watch_count, sort_order) VALUES (2, 1, 'ALL Question Correction', 'https://utkarsh4tech.github.io/BSMS2002/pages/extra_resources.html', 10, 1);
INSERT INTO resources (id, course_id, name, yt_link, watch_count, sort_order) VALUES (3, 4, 'MLT Best Notes', 'https://drive.google.com/file/d/1oINQmnCqK-WLvn1DrWyBYn_iMN5f8Ur5/view?usp=sharing', 56, 0);
INSERT INTO resources (id, course_id, name, yt_link, watch_count, sort_order) VALUES (1, 1, 'ALL ANOVA QUESTION HERE', 'https://docs.google.com/document/d/1H2GT0n6huAr9H7hdGzDhQlUWAPuiUQv7e3xP9hwbqEs/edit?usp=sharing', 89, 0);

-- Backup for table extra_stuff
DELETE FROM extra_stuff;
INSERT INTO extra_stuff (id, course_id, name, link) VALUES (1, 1, 'Course Grade Calculator', 'https://ba-quiz-calculator.vercel.app/');

-- Backup for table feedback
DELETE FROM feedback;
INSERT INTO feedback (id, username, feedback, created_at) VALUES (1, 'Sudiksha', 'Heartfelt thanks to you! 
Your videos are truly life savers, my end-moment rescue. Because of your notes, quiz practice, and summary videos, I was able to understand concepts so easily and secure A and S grades in every subject. With minimum effort, I achieved maximum results. Truly grateful for the way you support students so selflessly, without expecting anything in return ❤️', 2025-09-02 12:36:18);
INSERT INTO feedback (id, username, feedback, created_at) VALUES (2, 'SMS', 'Brother, your videos are really great. They feel very friendly, just like when a friend explains before exams—we often learn more from them than in class. I felt the same while watching your videos and learned a lot. Even though I don’t understand Hindi much, your explanations made everything clear. Hope my fellow peers feel the same too. Thank you so much for the help, brother.', 2025-09-03 06:27:30);
INSERT INTO feedback (id, username, feedback, created_at) VALUES (3, 'Ayushi Patel', 'Your videos feel like a friend guiding me through tough topics—clear, calm, and super helpful. Even with limited time, your notes and quizzes helped me score top grades. So grateful for your selfless support ❤️.', 2025-09-06 07:11:34);
INSERT INTO feedback (id, username, feedback, created_at) VALUES (5, 'sample', 'acosjci', 2025-11-24 04:35:08.954104);
