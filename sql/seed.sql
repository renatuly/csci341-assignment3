-- CSCI 341 Assignment 3 -- fictional seed data. Run after schema.sql.
-- All people, institutions and conferences are fictional.

-- ---------------------------------------------------------------- users (13)
INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1,  'Arman',   'Armanov',   'arman.armanov@example.com',   'Nazarbayev University',      'Kazakhstan', '+77011112233'),
 (2,  'Amina',   'Aminova',   'amina.aminova@example.com',   'Astana IT University',       'Kazakhstan', '+77022223344'),
 (3,  'Dana',    'Bekova',    'dana.bekova@example.com',     'Nazarbayev University',      'Kazakhstan', '+77033334455'),
 (4,  'Yerlan',  'Sadykov',   'yerlan.sadykov@example.com',  'KBTU',                       'Kazakhstan', '+77044445566'),
 (5,  'Aigerim', 'Nurlanova', 'aigerim.nurlanova@example.com','Al-Farabi KazNU',           'Kazakhstan', '+77055556677'),
 (6,  'Timur',   'Akhmetov',  'timur.akhmetov@example.com',  'Satbayev University',        'Kazakhstan', '+77066667788'),
 (7,  'Saule',   'Omarova',   'saule.omarova@example.com',   'Astana IT University',       'Kazakhstan', '+77077778899'),
 (8,  'Daniyar', 'Kassym',    'daniyar.kassym@example.com',  'SDU University',             'Kazakhstan', '+77088889900'),
 (9,  'Maria',   'Ivanova',   'maria.ivanova@example.com',   'Novosibirsk State University','Russia',    '+79131234567'),
 (10, 'John',    'Smith',     'john.smith@example.com',      'University of Leeds',        'United Kingdom','+441132345678'),
 (11, 'Li',      'Wei',       'li.wei@example.com',          'Tsinghua University',        'China',      '+861062781234'),
 (12, 'Elena',   'Petrova',   'elena.petrova@example.com',   'ITMO University',            'Russia',     '+78123456789'),
 (13, 'Ahmed',   'Khan',      'ahmed.khan@example.com',      'LUMS',                       'Pakistan',   '+924235608000');

-- Authors: 1, 2, 5, 6, 8, 9, 11, 13   (author-only: 2, 6, 9, 11, 13)
INSERT INTO author (author_id, orcid) VALUES
 (1, '0000-0001-1111-0001'), (2, '0000-0002-2222-0002'), (5, NULL), (6, '0000-0003-3333-0003'),
 (8, NULL), (9, '0000-0004-4444-000X'), (11, NULL), (13, '0000-0005-5555-0005');

INSERT INTO author_research_area (author_id, area_label) VALUES
 (1, 'Databases'), (1, 'Information Retrieval'),
 (2, 'Security'), (2, 'Distributed Systems'),
 (5, 'Machine Learning'),
 (6, 'Databases'), (6, 'Query Optimization'),
 (8, 'Machine Learning'), (8, 'Data Mining'),
 (9, 'Databases'),
 (11, 'Machine Learning'), (11, 'Databases'),
 (13, 'Computer Vision');

-- Reviewers: 1, 3, 4, 5, 7, 8, 10, 12   (reviewer-only: 3, 4, 7, 10, 12; both roles: 1, 5, 8)
INSERT INTO reviewer (reviewer_id, years_experience) VALUES
 (1, 6), (3, 5), (4, 8), (5, 3), (7, 2), (8, 4), (10, 10), (12, 4);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 (1, 'Databases'), (1, 'Information Retrieval'),
 (3, 'Databases'), (3, 'Data Management'),
 (4, 'Databases'), (4, 'Machine Learning'),
 (5, 'Machine Learning'), (5, 'Computer Vision'),
 (7, 'Databases'),
 (8, 'Machine Learning'), (8, 'Data Mining'),
 (10, 'Networks'), (10, 'Distributed Systems'),
 (12, 'Databases'), (12, 'Security');

-- ---------------------------------------------------------------- conferences (3)
INSERT INTO conference (conference_id, name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Astana International Conference on Data Management', 'AICDM 2026',
     'Database systems, query processing and data privacy.', 'Astana', 'Kazakhstan',
     '2026-06-10', '2026-06-12', '2026-02-15', '2026-04-15'),
 (2, 'Central Asian Symposium on Machine Learning', 'CASML 2026',
     'Machine learning methods and applications.', 'Almaty', 'Kazakhstan',
     '2026-09-21', '2026-09-23', '2026-05-01', '2026-07-20'),
 (3, 'Silk Road Workshop on Networked Systems', 'SRNET 2026',
     'Wireless and distributed networked systems.', 'Tashkent', 'Uzbekistan',
     '2026-11-05', '2026-11-06', '2026-08-01', '2026-09-15');

INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Nazarbayev University'), (1, 'Astana IT University'),
 (2, 'KBTU'),
 (3, 'Inha University in Tashkent'), (3, 'Tashkent University of IT');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
 (1, 1), (1, 3), (1, 4), (1, 7), (1, 12),
 (2, 4), (2, 5), (2, 8), (2, 10),
 (3, 1), (3, 10);

-- ---------------------------------------------------------------- tracks (6)
INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Data Management',  'Storage, indexing and transactions.',       'Databases',        3),
 (2, 1, 'Query Processing', 'Query optimization and execution.',         'Databases',        4),
 (3, 1, 'Data Privacy',     'Privacy-preserving data management.',       'Security',         12), -- empty track
 (4, 2, 'Deep Learning',    'Neural architectures and training.',        'Machine Learning', 5),
 (5, 2, 'ML Applications',  'Applied machine learning.',                 'Machine Learning', 8),
 (6, 3, 'Wireless Networks','Wireless and mobile networking.',           'Networks',         10); -- conference 3 has no papers

-- ---------------------------------------------------------------- sessions (5)
INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Storage and Indexing',  '2026-06-10', '10:00', '11:30', 'Room A1', 3),
 (2, 1, 'Query Optimization',    '2026-06-11', '14:00', '15:30', 'Room B2', 4),
 (3, 1, 'Poster Session',        '2026-06-12', '09:00', '10:00', 'Hall C',  12), -- empty, Astana
 (4, 2, 'Neural Models',         '2026-09-21', '11:00', '12:30', 'Room 101', 5),
 (5, 2, 'Applied ML Showcase',   '2026-09-22', '15:00', '16:00', 'Room 102', 10); -- empty, not Astana

-- ---------------------------------------------------------------- papers (13)
INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1,  1, 'Adaptive B+ Tree Indexing for Hybrid Workloads',
      'We present an adaptive B+ tree that reorganizes leaf nodes for mixed read and write workloads.',
      '2026-02-01', 'accepted', 1),
 (2,  1, 'Learned Cardinality Estimation',
      'This paper applies Machine Learning models to estimate join cardinalities in relational engines.',
      '2026-02-03', 'accepted', 2),
 (3,  2, 'Cost-Based Join Reordering Revisited',
      'A dynamic programming approach to join reordering with improved cost models.',
      '2026-02-05', 'accepted', 2),
 (4,  2, 'Incremental View Maintenance at Scale',
      'We maintain materialized views incrementally over large update streams.',
      '2026-02-07', 'accepted', NULL),
 (5,  2, 'Benchmarking Columnar Storage Engines',
      'An experimental comparison of columnar storage engines on analytical queries.',
      '2026-02-09', 'rejected', NULL),
 (6,  1, 'Schema Evolution in Document Stores',
      'We study how schemas evolve in document-oriented databases over time.',
      '2026-02-10', 'under review', NULL),
 (7,  1, 'Blockchain-Backed Audit Logs for DBMS',
      'An append-only audit log for database systems anchored on a blockchain.',
      '2026-02-11', 'withdrawn', NULL),
 (8,  4, 'Transformer Pruning for Edge Devices',
      'Structured pruning of transformer networks for low-power edge hardware.',
      '2026-04-20', 'accepted', 4),
 (9,  4, 'Contrastive Learning for Kazakh Speech',
      'Self-supervised contrastive pretraining for low-resource Kazakh speech recognition.',
      '2026-04-22', 'submitted', NULL),
 (10, 5, 'Crop Yield Prediction from Satellite Imagery',
      'We predict crop yield in northern Kazakhstan using machine learning on satellite images.',
      '2026-04-24', 'rejected', NULL),
 (11, 5, 'Federated Learning in Hospital Networks',
      'Privacy-aware federated training of diagnostic models across hospitals.',
      '2026-04-25', 'withdrawn', NULL),
 (12, 5, 'Graph Neural Networks for Traffic Forecasting',
      'Spatio-temporal graph neural networks for city traffic forecasting in Almaty.',
      '2026-04-27', 'accepted', NULL),
 (13, 4, 'Explainable Credit Scoring Models',
      'Post-hoc explanation techniques for neural credit scoring.',
      '2026-04-28', 'withdrawn', NULL);

-- Authorship (exactly one corresponding author per paper)
INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 5, 1, TRUE),  (1, 6, 2, FALSE),
 (2, 1, 1, TRUE),  (2, 9, 2, FALSE), (2, 11, 3, FALSE),
 (3, 6, 1, TRUE),  (3, 13, 2, FALSE),
 (4, 8, 1, TRUE),  (4, 5, 2, FALSE),
 (5, 9, 1, TRUE),
 (6, 11, 1, TRUE), (6, 2, 2, FALSE),
 (7, 2, 1, TRUE),  (7, 6, 2, FALSE),                  -- withdrawn, Amina corresponding
 (8, 13, 1, TRUE), (8, 1, 2, FALSE),
 (9, 5, 1, TRUE),
 (10, 8, 1, TRUE), (10, 11, 2, FALSE),
 (11, 9, 1, FALSE),(11, 2, 2, TRUE),                  -- withdrawn, Amina corresponding
 (12, 6, 1, TRUE), (12, 9, 2, FALSE),
 (13, 6, 1, TRUE), (13, 2, 2, FALSE);                 -- withdrawn, Amina is NOT corresponding

INSERT INTO paper_keyword (paper_id, keyword) VALUES
 (1, 'B+ tree'), (1, 'indexing'),
 (2, 'cardinality estimation'), (2, 'machine learning'),
 (3, 'join ordering'), (3, 'query optimization'),
 (4, 'materialized views'),
 (5, 'columnar storage'), (5, 'benchmarking'),
 (6, 'schema evolution'), (6, 'NoSQL'),
 (7, 'blockchain'), (7, 'auditing'),
 (8, 'transformers'), (8, 'pruning'),
 (9, 'speech recognition'), (9, 'contrastive learning'),
 (10, 'remote sensing'), (10, 'agriculture'),
 (11, 'federated learning'), (11, 'healthcare'),
 (12, 'graph neural networks'), (12, 'traffic'),
 (13, 'explainability');

-- Versions (gaps allowed; highest number = current version)
INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, '/files/papers/1/v1.pdf', '2026-02-01 09:15:00', NULL),
 (1, 2, '/files/papers/1/v2.pdf', '2026-03-20 18:40:00', 'Addressed reviewer comments'),
 (1, 3, '/files/papers/1/v3.pdf', '2026-05-02 11:05:00', 'Camera-ready version'),
 (2, 1, '/files/papers/2/v1.pdf', '2026-02-03 14:00:00', NULL),
 (3, 1, '/files/papers/3/v1.pdf', '2026-02-05 10:30:00', NULL),
 (3, 3, '/files/papers/3/v3.pdf', '2026-04-30 16:20:00', 'Camera-ready (v2 skipped)'),
 (4, 1, '/files/papers/4/v1.pdf', '2026-02-07 12:00:00', NULL),
 (5, 1, '/files/papers/5/v1.pdf', '2026-02-09 08:45:00', NULL),
 (6, 1, '/files/papers/6/v1.pdf', '2026-02-10 19:10:00', NULL),
 (7, 1, '/files/papers/7/v1.pdf', '2026-02-11 21:00:00', NULL),
 (7, 2, '/files/papers/7/v2.pdf', '2026-02-14 10:00:00', 'Fixed figures'),
 (8, 1, '/files/papers/8/v1.pdf', '2026-04-20 09:00:00', NULL),
 (8, 2, '/files/papers/8/v2.pdf', '2026-07-30 13:30:00', 'Camera-ready version'),
 (9, 1, '/files/papers/9/v1.pdf', '2026-04-22 15:45:00', NULL),
 (10, 1, '/files/papers/10/v1.pdf', '2026-04-24 17:00:00', NULL),
 (11, 1, '/files/papers/11/v1.pdf', '2026-04-25 11:11:00', NULL),
 (12, 1, '/files/papers/12/v1.pdf', '2026-04-27 10:00:00', NULL),
 (13, 1, '/files/papers/13/v1.pdf', '2026-04-28 09:30:00', NULL);

-- ---------------------------------------------------------------- reviews (18, completed only)
-- Review counts: Bekova 4, Sadykov 5, Petrova 3, Armanov 2, Smith 2, Nurlanova 1, Kassym 1, Omarova 0
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1,  1, 3,  5, 'accept', 'Strong experimental section.',            NULL,                         '2026-03-10'),
 (2,  1, 4,  4, 'accept', 'Clear motivation; minor typos.',          NULL,                         '2026-03-12'),
 (3,  1, 12, 4, 'accept', 'Good work, compare with LSM trees.',      'Could be a best-paper candidate.', '2026-03-14'),
 (4,  2, 3,  4, 'accept', 'Interesting use of learned models.',      NULL,                         '2026-03-11'),
 (5,  2, 4,  5, 'accept', 'Excellent and well written.',             NULL,                         '2026-03-15'),
 (6,  3, 3,  4, 'accept', 'Solid contribution.',                     NULL,                         '2026-03-16'),
 (7,  3, 1,  5, 'accept', 'Convincing cost model evaluation.',       NULL,                         '2026-03-18'),
 (8,  4, 12, 4, 'accept', 'Useful for practitioners.',               NULL,                         '2026-03-20'),
 (9,  4, 4,  3, 'accept', 'Acceptable, limited novelty.',            'Borderline.',                '2026-03-21'),
 (10, 5, 3,  2, 'reject', 'Benchmarks are not reproducible.',        NULL,                         '2026-03-22'),
 (11, 5, 12, 1, 'reject', 'Missing several baseline systems.',       NULL,                         '2026-03-23'),
 (12, 6, 1,  3, 'accept', 'Promising but needs more datasets.',      NULL,                         '2026-03-25'),
 (13, 7, 4,  2, 'reject', 'Threat model is unclear.',                NULL,                         '2026-03-02'),
 (14, 8, 10, 5, 'accept', 'Impressive speed-ups on real devices.',   NULL,                         '2026-06-10'),
 (15, 10, 4, 2, 'reject', 'Evaluation region is too small.',         NULL,                         '2026-06-12'),
 (16, 10, 10, 1, 'reject', 'No comparison with existing models.',    'Possible duplicate submission.', '2026-06-14'),
 (17, 12, 5, 4, 'accept', 'Well-motivated application.',             NULL,                         '2026-06-15'),
 (18, 11, 8, 3, 'reject', 'Privacy guarantees are not formalised.',  NULL,                         '2026-06-01');

-- Move identity counters past the explicit IDs used above
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),              (SELECT MAX(user_id) FROM app_user));
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),      (SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track', 'track_id'),                (SELECT MAX(track_id) FROM track));
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'), (SELECT MAX(session_id) FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),                (SELECT MAX(paper_id) FROM paper));
SELECT setval(pg_get_serial_sequence('review', 'review_id'),              (SELECT MAX(review_id) FROM review));
