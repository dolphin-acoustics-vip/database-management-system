/*!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.6.18-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: test_database
-- ------------------------------------------------------
-- Server version	10.6.18-MariaDB-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `assignment`
--

DROP TABLE IF EXISTS `assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `assignment` (
  `user_id` varchar(36) NOT NULL,
  `recording_id` varchar(36) NOT NULL,
  `created_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  `completed_flag` tinyint(1) NOT NULL DEFAULT 0,
  `notes` text DEFAULT NULL,
  PRIMARY KEY (`user_id`,`recording_id`),
  KEY `recording_id_fk` (`recording_id`),
  CONSTRAINT `recording_id_fk` FOREIGN KEY (`recording_id`) REFERENCES `recording` (`id`),
  CONSTRAINT `user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignment`
--

LOCK TABLES `assignment` WRITE;
/*!40000 ALTER TABLE `assignment` DISABLE KEYS */;
/*!40000 ALTER TABLE `assignment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `data_source`
--

DROP TABLE IF EXISTS `data_source`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `data_source` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `name` varchar(255) NOT NULL,
  `phone_number1` varchar(20) DEFAULT NULL,
  `phone_number2` varchar(20) DEFAULT NULL,
  `email1` varchar(255) NOT NULL,
  `email2` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `type` enum('person','organisation') DEFAULT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`,`email1`),
  KEY `fk_updated_by_id_data_source` (`updated_by_id`),
  CONSTRAINT `fk_updated_by_id_data_source` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `encounter`
--

DROP TABLE IF EXISTS `encounter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `encounter` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `encounter_date` date DEFAULT NULL,
  `file_timezone` int(4) DEFAULT NULL,
  `local_timezone` int(4) DEFAULT NULL,
  `encounter_name` varchar(100) NOT NULL,
  `location` varchar(100) NOT NULL,
  `species_id` varchar(36) NOT NULL,
  `project` varchar(100) NOT NULL,
  `longitude` double DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `notes` varchar(1000) DEFAULT NULL,
  `date_received` date DEFAULT NULL,
  `data_source_id` varchar(36) DEFAULT NULL,
  `recording_platform_id` varchar(36) DEFAULT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `created_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `encounter_name_location_project` (`encounter_name`,`location`,`project`),
  KEY `species_id` (`species_id`),
  KEY `data_source_id` (`data_source_id`),
  KEY `recording_platform_id` (`recording_platform_id`),
  KEY `fk_updated_by_id_encounter` (`updated_by_id`),
  CONSTRAINT `encounter_ibfk_1` FOREIGN KEY (`species_id`) REFERENCES `species` (`id`),
  CONSTRAINT `encounter_ibfk_2` FOREIGN KEY (`data_source_id`) REFERENCES `data_source` (`id`),
  CONSTRAINT `encounter_ibfk_3` FOREIGN KEY (`recording_platform_id`) REFERENCES `recording_platform` (`id`),
  CONSTRAINT `fk_updated_by_id_encounter` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `encounter`
--

LOCK TABLES `encounter` WRITE;
/*!40000 ALTER TABLE `encounter` DISABLE KEYS */;
/*!40000 ALTER TABLE `encounter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `file`
--

DROP TABLE IF EXISTS `file`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `file` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `path` text NOT NULL,
  `filename` varchar(255) NOT NULL,
  `extension` varchar(10) NOT NULL,
  `uploaded_date` datetime DEFAULT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `upload_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  `original_filename` varchar(255) DEFAULT NULL,
  `temp` tinyint(1) NOT NULL DEFAULT 0,
  `deleted` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `fk_updated_by_id_file` (`updated_by_id`),
  CONSTRAINT `fk_updated_by_id_file` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `file`
--

LOCK TABLES `file` WRITE;
/*!40000 ALTER TABLE `file` DISABLE KEYS */;
/*!40000 ALTER TABLE `file` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recording`
--

DROP TABLE IF EXISTS `recording`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recording` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `start_time` datetime NOT NULL,
  `duration` int(11) DEFAULT NULL,
  `recording_file_id` varchar(36) DEFAULT NULL,
  `selection_table_file_id` varchar(36) DEFAULT NULL,
  `encounter_id` varchar(36) NOT NULL,
  `ignore_selection_table_warnings` tinyint(1) NOT NULL DEFAULT 0,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `created_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  `status` enum('Unassigned','In Progress','Awaiting Review','Reviewed','On Hold') DEFAULT 'Unassigned',
  `status_change_datetime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `notes` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_time_encounter_id` (`start_time`,`encounter_id`),
  KEY `fk_encounter_id` (`encounter_id`),
  KEY `fk_recording_file_id` (`recording_file_id`),
  KEY `fk_selection_table_file_id` (`selection_table_file_id`),
  KEY `fk_updated_by_id_recording` (`updated_by_id`),
  CONSTRAINT `fk_encounter_id` FOREIGN KEY (`encounter_id`) REFERENCES `encounter` (`id`),
  CONSTRAINT `fk_recording_file_id` FOREIGN KEY (`recording_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_selection_table_file_id` FOREIGN KEY (`selection_table_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_updated_by_id_recording` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recording`
--

LOCK TABLES `recording` WRITE;
/*!40000 ALTER TABLE `recording` DISABLE KEYS */;
/*!40000 ALTER TABLE `recording` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recording_platform`
--

DROP TABLE IF EXISTS `recording_platform`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recording_platform` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `name` varchar(100) NOT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name` (`name`),
  KEY `fk_updated_by_id_recording_platform` (`updated_by_id`),
  CONSTRAINT `fk_updated_by_id_recording_platform` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `role`
--

DROP TABLE IF EXISTS `role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `role` (
  `id` int(11) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `role`
--

LOCK TABLES `role` WRITE;
/*!40000 ALTER TABLE `role` DISABLE KEYS */;
INSERT INTO `role` VALUES (2,'Database Administrator'),(3,'General User'),(1,'System Administrator'),(4,'View Only');
/*!40000 ALTER TABLE `role` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `selection`
--

DROP TABLE IF EXISTS `selection`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `selection` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `selection_number` int(11) NOT NULL,
  `selection_file_id` varchar(36) DEFAULT NULL,
  `recording_id` varchar(36) NOT NULL,
  `contour_file_id` varchar(36) DEFAULT NULL,
  `sampling_rate` double DEFAULT NULL,
  `view` varchar(30) DEFAULT NULL,
  `channel` int(4) DEFAULT NULL,
  `begin_time` double DEFAULT NULL,
  `end_time` double DEFAULT NULL,
  `low_frequency` double DEFAULT NULL,
  `high_frequency` double DEFAULT NULL,
  `delta_time` double DEFAULT NULL,
  `delta_frequency` double DEFAULT NULL,
  `average_power` double DEFAULT NULL,
  `annotation` varchar(10) DEFAULT NULL,
  `traced` tinyint(1) DEFAULT NULL,
  `deactivated` tinyint(1) DEFAULT 0,
  `freq_max` double DEFAULT NULL,
  `freq_min` double DEFAULT NULL,
  `duration` double DEFAULT NULL,
  `freq_begin` double DEFAULT NULL,
  `freq_end` double DEFAULT NULL,
  `freq_range` double DEFAULT NULL,
  `dc_mean` double DEFAULT NULL,
  `dc_standarddeviation` double DEFAULT NULL,
  `freq_mean` double DEFAULT NULL,
  `freq_standarddeviation` double DEFAULT NULL,
  `freq_median` double DEFAULT NULL,
  `freq_center` double DEFAULT NULL,
  `freq_relbw` double DEFAULT NULL,
  `freq_maxminratio` double DEFAULT NULL,
  `freq_begendratio` double DEFAULT NULL,
  `freq_quarter1` double DEFAULT NULL,
  `freq_quarter2` double DEFAULT NULL,
  `freq_quarter3` double DEFAULT NULL,
  `freq_spread` double DEFAULT NULL,
  `dc_quarter1mean` double DEFAULT NULL,
  `dc_quarter2mean` double DEFAULT NULL,
  `dc_quarter3mean` double DEFAULT NULL,
  `dc_quarter4mean` double DEFAULT NULL,
  `freq_cofm` double DEFAULT NULL,
  `freq_stepup` int(4) DEFAULT NULL,
  `freq_stepdown` int(4) DEFAULT NULL,
  `freq_numsteps` int(4) DEFAULT NULL,
  `freq_slopemean` double DEFAULT NULL,
  `freq_absslopemean` double DEFAULT NULL,
  `freq_posslopemean` double DEFAULT NULL,
  `freq_negslopemean` double DEFAULT NULL,
  `freq_sloperatio` double DEFAULT NULL,
  `freq_begsweep` int(4) DEFAULT NULL,
  `freq_begup` int(4) DEFAULT NULL,
  `freq_begdown` int(4) DEFAULT NULL,
  `freq_endsweep` int(4) DEFAULT NULL,
  `freq_endup` int(4) DEFAULT NULL,
  `freq_enddown` int(4) DEFAULT NULL,
  `num_sweepsupdown` int(4) DEFAULT NULL,
  `num_sweepsdownup` int(4) DEFAULT NULL,
  `num_sweepsupflat` int(4) DEFAULT NULL,
  `num_sweepsdownflat` int(4) DEFAULT NULL,
  `num_sweepsflatup` int(4) DEFAULT NULL,
  `num_sweepsflatdown` int(4) DEFAULT NULL,
  `freq_sweepuppercent` double DEFAULT NULL,
  `freq_sweepdownpercent` double DEFAULT NULL,
  `freq_sweepflatpercent` double DEFAULT NULL,
  `num_inflections` int(4) DEFAULT NULL,
  `inflection_maxdelta` double DEFAULT NULL,
  `inflection_mindelta` double DEFAULT NULL,
  `inflection_maxmindelta` double DEFAULT NULL,
  `inflection_meandelta` double DEFAULT NULL,
  `inflection_standarddeviationdelta` double DEFAULT NULL,
  `inflection_mediandelta` double DEFAULT NULL,
  `inflection_duration` double DEFAULT NULL,
  `step_duration` double DEFAULT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `ctr_file_id` varchar(36) DEFAULT NULL,
  `spectogram_file_id` varchar(36) DEFAULT NULL,
  `plot_file_id` varchar(36) DEFAULT NULL,
  `default_fft_size` int(4) DEFAULT NULL,
  `deactivate_selection` tinyint(1) NOT NULL DEFAULT 0,
  `default_hop_size` int(4) DEFAULT NULL,
  `created_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `selection_number` (`selection_number`,`recording_id`),
  KEY `fk_updated_by_id_selection` (`updated_by_id`),
  KEY `recording_id` (`recording_id`),
  KEY `fk_selection_file_id` (`selection_file_id`),
  KEY `fk_contour_file_id` (`contour_file_id`),
  KEY `fk_ctr_file_id` (`ctr_file_id`),
  KEY `fk_spectogram_file_id` (`spectogram_file_id`),
  KEY `fk_plot_file_id` (`plot_file_id`),
  CONSTRAINT `fk_contour_file_id` FOREIGN KEY (`contour_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_ctr_file_id` FOREIGN KEY (`ctr_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_plot_file_id` FOREIGN KEY (`plot_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_selection_file_id` FOREIGN KEY (`selection_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_spectogram_file_id` FOREIGN KEY (`spectogram_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_updated_by_id_selection` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `selection_ibfk_1` FOREIGN KEY (`recording_id`) REFERENCES `recording` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `selection`
--

LOCK TABLES `selection` WRITE;
/*!40000 ALTER TABLE `selection` DISABLE KEYS */;
/*!40000 ALTER TABLE `selection` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `species`
--

DROP TABLE IF EXISTS `species`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `species` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `species_name` varchar(100) NOT NULL,
  `genus_name` varchar(100) DEFAULT NULL,
  `common_name` varchar(100) DEFAULT NULL,
  `updated_by_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `species_name` (`species_name`),
  KEY `fk_updated_by_id_species` (`updated_by_id`),
  CONSTRAINT `fk_updated_by_id_species` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci WITH SYSTEM VERSIONING;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `species`
--

LOCK TABLES `species` WRITE;
/*!40000 ALTER TABLE `species` DISABLE KEYS */;
INSERT INTO `species` VALUES (uuid(),'Pseudorca craissidens','Pseudorca','False killer whale',''),(uuid(),'Steno','Steno','Rough Toothed Dolphin','');
/*!40000 ALTER TABLE `species` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `login_id` varchar(100) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `name` varchar(1000) DEFAULT NULL,
  `role_id` int(11) NOT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `expiry` date DEFAULT (curdate() + interval 1 year),
  `is_temporary` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `login_id` (`login_id`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `user_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (uuid(),'admin@testmail.com','password','Init Admin',1,1,"3000-01-01",0);
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-09-02 10:21:07
