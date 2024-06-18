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
-- Table structure for table `data_source`
--

DROP TABLE IF EXISTS `data_source`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `data_source` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `name` varchar(255) NOT NULL,
  `phone_number1` varchar(20) DEFAULT NULL,
  `phone_number2` varchar(20) DEFAULT NULL,
  `email1` varchar(255) NOT NULL,
  `email2` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `type` enum('person','organisation') DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`,`email1`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `encounter`
--

DROP TABLE IF EXISTS `encounter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `encounter` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `encounter_name` varchar(100) NOT NULL,
  `location` varchar(100) NOT NULL,
  `species_id` uuid NOT NULL,
  `origin` varchar(100) DEFAULT NULL,
  `longitude` varchar(20) DEFAULT NULL,
  `latitude` varchar(20) DEFAULT NULL,
  `notes` varchar(1000) DEFAULT NULL,
  `date_received` date DEFAULT NULL,
  `data_source_id` uuid DEFAULT NULL,
  `recording_platform_id` uuid DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `encounter_name` (`encounter_name`,`location`),
  KEY `species_id` (`species_id`),
  KEY `data_source_id` (`data_source_id`),
  KEY `recording_platform_id` (`recording_platform_id`),
  CONSTRAINT `encounter_ibfk_1` FOREIGN KEY (`species_id`) REFERENCES `species` (`id`),
  CONSTRAINT `encounter_ibfk_2` FOREIGN KEY (`data_source_id`) REFERENCES `data_source` (`id`),
  CONSTRAINT `encounter_ibfk_3` FOREIGN KEY (`recording_platform_id`) REFERENCES `recording_platform` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `file`
--

DROP TABLE IF EXISTS `file`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `file` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `path` text NOT NULL,
  `filename` varchar(255) NOT NULL,
  `extension` varchar(10) NOT NULL,
  `uploaded_date` datetime DEFAULT NULL,
  `uploaded_by` varchar(100) DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `recording`
--

DROP TABLE IF EXISTS `recording`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recording` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `start_time` datetime NOT NULL,
  `duration` int(11) DEFAULT NULL,
  `recording_file_id` uuid DEFAULT NULL,
  `selection_table_file_id` uuid DEFAULT NULL,
  `encounter_id` uuid NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_time_encounter_id` (`start_time`,`encounter_id`),
  KEY `fk_encounter_id` (`encounter_id`),
  KEY `fk_recording_file_id` (`recording_file_id`),
  KEY `fk_selection_table_file_id` (`selection_table_file_id`),
  CONSTRAINT `fk_encounter_id` FOREIGN KEY (`encounter_id`) REFERENCES `encounter` (`id`),
  CONSTRAINT `fk_recording_file_id` FOREIGN KEY (`recording_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_selection_table_file_id` FOREIGN KEY (`selection_table_file_id`) REFERENCES `file` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;



CREATE TABLE `recording_audit` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `action` varchar(50) NOT NULL,
  `record_id` uuid NOT NULL,
  `start_time_old` datetime DEFAULT NULL,
  `start_time_new` datetime DEFAULT NULL,
  `duration_old` int(11) DEFAULT NULL,
  `duration_new` int(11) DEFAULT NULL,
  `recording_file_id_old` uuid DEFAULT NULL,
  `recording_file_id_new` uuid DEFAULT NULL,
  `selection_table_file_id_old` uuid DEFAULT NULL,
  `selection_table_file_id_new` uuid DEFAULT NULL,
  `encounter_id_old` uuid DEFAULT NULL,
  `encounter_id_new` uuid DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_record_id` (`record_id`),
  CONSTRAINT `fk_record_id` FOREIGN KEY (`record_id`) REFERENCES `recording` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

DELIMITER //
CREATE TRIGGER recording_audit_trigger
AFTER INSERT ON recording
FOR EACH ROW
BEGIN
  INSERT INTO recording_audit (created_at, updated_at, action, record_id, start_time_new, duration_new, recording_file_id_new, selection_table_file_id_new, encounter_id_new)
  VALUES ( UTC_TIMESTAMP(), UTC_TIMESTAMP(), 'CREATE', NEW.id, NEW.start_time, NEW.duration, NEW.recording_file_id, NEW.selection_table_file_id, NEW.encounter_id);
END;
//

DELIMITER //
CREATE TRIGGER recording_update_audit_trigger
AFTER UPDATE ON recording
FOR EACH ROW
BEGIN
  INSERT INTO recording_audit (created_at, updated_at, action, record_id, start_time_old, start_time_new, duration_old, duration_new, recording_file_id_old, recording_file_id_new, selection_table_file_id_old, selection_table_file_id_new, encounter_id_old, encounter_id_new)
  VALUES ( UTC_TIMESTAMP(),  UTC_TIMESTAMP(), 'UPDATE', OLD.id, OLD.start_time, NEW.start_time, OLD.duration, NEW.duration, OLD.recording_file_id, NEW.recording_file_id, OLD.selection_table_file_id, NEW.selection_table_file_id, OLD.encounter_id, NEW.encounter_id);
END;
//

DELIMITER //
CREATE TRIGGER recording_delete_audit_trigger
AFTER DELETE ON recording
FOR EACH ROW
BEGIN
  INSERT INTO recording_audit (created_at, updated_at, action, record_id, start_time_old, duration_old, recording_file_id_old, selection_table_file_id_old, encounter_id_old)
  VALUES ( UTC_TIMESTAMP(),  UTC_TIMESTAMP(), 'DELETE', OLD.id, OLD.start_time, OLD.duration, OLD.recording_file_id, OLD.selection_table_file_id, OLD.encounter_id);
END;
//

--
-- Table structure for table `recording_platform`
--

DROP TABLE IF EXISTS `recording_platform`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recording_platform` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `selection`
--

DROP TABLE IF EXISTS `selection`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `selection` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `selection_number` int(11) NOT NULL,
  `selection_file_id` uuid NOT NULL,
  `recording_id` uuid NOT NULL,
  `contour_file_id` uuid,

  `freq_max` float,
  `freq_min` float,
  `duration` float,
  `freq_begin` float,
  `freq_end` float,
  `freq_range` float,
  `dc_mean` float,
  `dc_standarddeviation` float,
  `freq_mean` float,
  `freq_standarddeviation` float,
  `freq_median` float,
  `freq_center` float,
  `freq_relbw` float,
  `freq_maxminration` float,
  `freq_begendratio` float,
  `freq_quarter1` float,
  `freq_quarter2` float,
  `freq_quarter3` float,
  `freq_spread` float,
  `dc_quarter1mean` float,
  `dc_quarter2mean` float,
  `dc_quarter3mean` float,
  `dc_quarter4mean` float,
  `freq_cofm` float,
  `freq_stepup` int(4),
  `freq_stepdown` int(4),
  `freq_numsteps` int(4),
  `freq_slopemean` float,
  `freq_absslopemean` float,
  `freq_posslopemean` float,
  `freq_negslopemean` float,
  `freq_sloperatio` float,
  `freq_begsweep` int(4),
  `freq_begup` int(4),
  `freq_begdown` int(4),
  `freq_endsweep` int(4),
  `freq_endup` int(4),
  `freq_enddown` int(4),
  `num_sweepsupdown` int(4),
  `num_sweepsdownup` int(4),
  `num_sweepsupflat` int(4),
  `num_sweepsdownflat` int(4),
  `num_sweepsflatup` int(4),
  `num_sweepsflatdown` int(4),
  `freq_sweepuppercent` float,
  `freq_sweepdownpercent` float,
  `freq_sweepflatpercent` float,
  `num_inflections` int(4),
  `inflection_maxdelta` float,
  `inflection_mindelta` float,
  `inflection_maxmindelta` float,
  `inflection_meandelta` float,
  `inflection_standarddeviationdelta` float,
  `inflection_duration` float,
  `step_duration` float,
  `freq_peak` float,
  `bw3db` float,
  `bw3dblow` float,
  `bw3dbhigh` float,
  `bw10db` float,
  `bw10dblow` float,
  `bw10dbhigh` float,
  `rms_signal` float,
  `rms_noise` float,
  `snr` float,
  `num_crossings` int(4),
  `sweep_rate` float,
  `mean_timezc` float,
  `median_timezc` float,
  `variance_timezc` float,
  `whale_train` float,

  PRIMARY KEY (`id`),
  UNIQUE KEY `selection_number` (`selection_number`,`recording_id`),
  KEY `recording_id` (`recording_id`),
  CONSTRAINT `selection_ibfk_1` FOREIGN KEY (`recording_id`) REFERENCES `recording` (`id`),
  CONSTRAINT `fk_selection_file_id` FOREIGN KEY (`selection_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_contour_file_id` FOREIGN KEY (`contour_file_id`) REFERENCES `file` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `species`
--

DROP TABLE IF EXISTS `species`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `species` (
  `id` uuid NOT NULL DEFAULT uuid(),
  `species_name` varchar(100) NOT NULL,
  `genus_name` varchar(100) DEFAULT NULL,
  `common_name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `species_name` (`species_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-03-27 19:55:34