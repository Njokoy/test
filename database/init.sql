CREATE DATABASE IF NOT EXISTS movies;

USE movies;

CREATE TABLE movies (
  name   VARCHAR(255),
  rating DOUBLE
);

INSERT INTO movies VALUES ("The Dark Knight", 8.1);
INSERT INTO movies VALUES ("Inception", 5.7);
INSERT INTO movies VALUES ("The Matrix", 9.9);
INSERT INTO movies VALUES ("The Lord of the Rings", 11.0);
INSERT INTO movies VALUES ("Star Wars", 3.4);
INSERT INTO movies VALUES ("Saving Private Ryan", 4.5);
INSERT INTO movies VALUES ("The Green Mile", 10.0);
INSERT INTO movies VALUES ("Gladiator", 1.1);
INSERT INTO movies VALUES ("Logan", 8.5);
INSERT INTO movies VALUES ("The Godfather", 9.2);
INSERT INTO movies VALUES ("Pulp Fiction", 8.9);
INSERT INTO movies VALUES ("Forrest Gump", 8.8);
INSERT INTO movies VALUES ("The Shawshank Redemption", 9.3);
INSERT INTO movies VALUES ("Schindler's List", 8.9);
INSERT INTO movies VALUES ("Fight Club", 8.8);
INSERT INTO movies VALUES ("The Lord of the Rings: The Return of the King", 8.9);
INSERT INTO movies VALUES ("The Dark Knight Rises", 7.6);
INSERT INTO movies VALUES ("Interstellar", 8.6);
INSERT INTO movies VALUES ("Avengers: Endgame", 8.4);
INSERT INTO movies VALUES ("Parasite", 8.5);
INSERT INTO movies VALUES ("Joker", 8.4);
INSERT INTO movies VALUES ("Titanic", 7.8);
INSERT INTO movies VALUES ("Inglourious Basterds", 8.3);
INSERT INTO movies VALUES ("Goodfellas", 8.7);
INSERT INTO movies VALUES ("The Silence of the Lambs", 8.6);
INSERT INTO movies VALUES ("Django Unchained", 8.4);
INSERT INTO movies VALUES ("The Lion King", 8.5);
INSERT INTO movies VALUES ("Whiplash", 8.5);
INSERT INTO movies VALUES ("Mad Max: Fury Road", 8.1);
INSERT INTO movies VALUES ("The Revenant", 8.0);
INSERT INTO movies VALUES ("Black Panther", 7.3);
INSERT INTO movies VALUES ("Spider-Man: No Way Home", 8.2);
INSERT INTO movies VALUES ("The Grand Budapest Hotel", 8.1);
INSERT INTO movies VALUES ("La La Land", 8.0);
INSERT INTO movies VALUES ("Get Out", 7.7);
INSERT INTO movies VALUES ("12 Years a Slave", 8.1);
INSERT INTO movies VALUES ("The Wolf of Wall Street", 8.2);
INSERT INTO movies VALUES ("Bohemian Rhapsody", 7.9);
INSERT INTO movies VALUES ("Oppenheimer", 8.5); 

-- Création de l'utilisateur zops
CREATE USER IF NOT EXISTS 'zops'@'%' IDENTIFIED BY 'zops2310';
GRANT ALL PRIVILEGES ON movies.* TO 'zops'@'%';
FLUSH PRIVILEGES;