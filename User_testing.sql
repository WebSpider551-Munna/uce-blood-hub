-- User_testing.sql: Populate users, user_profiles, and blood_requests tables with test data (no explicit IDs)

-- Insert users with different roles
INSERT INTO users (username, password, email, role) VALUES
('alice_admin', '$2b$12$adminhash', 'alice_admin@example.com', 'admin'),
('bob_coord', '$2b$12$coordhash', 'bob_coord@example.com', 'coordinator'),
('charlie_user', '$2b$12$userhash', 'charlie_user@example.com', 'user'),
('diana_user', '$2b$12$userhash2', 'diana_user@example.com', 'user'),
('eve_user', '$2b$12$userhash3', 'eve_user@example.com', 'user');

-- Insert user profiles for each user (using subqueries to get user_id)
INSERT INTO user_profiles (user_id, full_name, roll_no, blood_group, phone, branch, year, last_donation_date, is_available, photo_path, document_path) VALUES
((SELECT id FROM users WHERE username='alice_admin'), 'Alice Admin', 'IT2025001', 'A+', '9876543210', 'IT', 4, '2025-01-15', 1, '1_photo.jpg', '1_document.jpg'),
((SELECT id FROM users WHERE username='bob_coord'), 'Bob Coordinator', 'IT2025002', 'B-', '9123456789', 'IT', 3, '2025-02-10', 1, '2_photo.jpg', '2_document.jpg'),
((SELECT id FROM users WHERE username='charlie_user'), 'Charlie User', 'IT2025003', 'O+', '9988776655', 'CSE', 2, '2025-03-05', 1, '3_photo.jpg', '3_document.jpg'),
((SELECT id FROM users WHERE username='diana_user'), 'Diana User', 'IT2025004', 'AB+', '9001122334', 'ECE', 1, '2025-04-20', 0, '4_photo.jpg', '4_document.jpg'),
((SELECT id FROM users WHERE username='eve_user'), 'Eve User', 'IT2025005', 'A-', '9112233445', 'EEE', 2, '2025-05-18', 1, '5_photo.jpg', '5_document.jpg');

-- Insert blood requests for each user (using subqueries to get requester_id)
INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_required, hospital_name, urgency, contact_number, request_date, status) VALUES
((SELECT id FROM users WHERE username='charlie_user'), 'Patient One', 'A+', 2, 'City Hospital', 'high', '9988776655', '2025-06-01', 'pending'),
((SELECT id FROM users WHERE username='diana_user'), 'Patient Two', 'B-', 1, 'Metro Hospital', 'medium', '9001122334', '2025-06-02', 'fulfilled'),
((SELECT id FROM users WHERE username='eve_user'), 'Patient Three', 'O+', 3, 'General Hospital', 'critical', '9112233445', '2025-06-03', 'pending'),
((SELECT id FROM users WHERE username='bob_coord'), 'Patient Four', 'AB+', 2, 'Care Hospital', 'low', '9123456789', '2025-06-04', 'cancelled'),
((SELECT id FROM users WHERE username='alice_admin'), 'Patient Five', 'A-', 1, 'Super Hospital', 'high', '9876543210', '2025-06-05', 'pending');
