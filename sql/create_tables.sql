-- Creation of basic table to store the data
-- Store the following: 
-- Api Route
-- Method type
-- Domain
-- Request body
-- Response body
-- Response code
-- Date

CREATE TABLE IF NOT EXISTS history (
  id SERIAL NOT NULL,
  route varchar(100) NOT NULL,
  method varchar(10) NOT NULL,
  domain varchar(50) NOT NULL,
  req_body varchar(50) NOT NULL,
  res_code INT NOT NULL,
  res_body json NOT NULL,
  created_at date DEFAULT CURRENT_DATE,
  PRIMARY KEY (id)
);