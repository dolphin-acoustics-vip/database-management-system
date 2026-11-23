-- ARTwarp results tables (see the Job, Category, ReferenceContour and Contour models).

-- An ARTwarp run uploaded by a user, with the network parameters it used and its output files.
CREATE TABLE IF NOT EXISTS `job` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `user_id` varchar(36) NOT NULL,
  `upload_datetime` datetime NOT NULL DEFAULT current_timestamp(),
  `complete_output_id` varchar(36),
  `discovery_curve_id` varchar(36),
  `warpFactorLevel` int NOT NULL DEFAULT 3,
  `vigilance` int NOT NULL DEFAULT 95,
  `maxNumCategories` int,
  `maxNumIterations` int,
  `bias` double NOT NULL DEFAULT 0.000001,
  `learningRate` double NOT NULL DEFAULT 0.1,
  `resample` tinyint(1) NOT NULL DEFAULT 1,
  `sampleInterval` double NOT NULL DEFAULT 0.01,
  `compareWarped` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `fk_user_id` (`user_id`),
  KEY `fk_complete_output_id` (`complete_output_id`),
  KEY `fk_discovery_curve_id` (`discovery_curve_id`),
  CONSTRAINT `fk_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_complete_output_id` FOREIGN KEY (`complete_output_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_discovery_curve_id` FOREIGN KEY (`discovery_curve_id`) REFERENCES `file` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- A category found by a job.
CREATE TABLE IF NOT EXISTS `category` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `job_id` varchar(36) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `category_number` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_category_job` (`job_id`),
  CONSTRAINT `fk_category_job` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- The reference contour of a category (CSV and CTR files).
CREATE TABLE IF NOT EXISTS `reference_contour` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `category_id` varchar(36) NOT NULL,
  `contour_file_csv_id` varchar(36) DEFAULT NULL,
  `contour_file_ctr_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_ref_contour_category` (`category_id`),
  KEY `fk_ref_contour_csv_file` (`contour_file_csv_id`),
  KEY `fk_ref_contour_ctr_file` (`contour_file_ctr_id`),
  CONSTRAINT `fk_ref_contour_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`),
  CONSTRAINT `fk_ref_contour_csv_file` FOREIGN KEY (`contour_file_csv_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_ref_contour_ctr_file` FOREIGN KEY (`contour_file_ctr_id`) REFERENCES `file` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- A contour (selection) assigned to a category.
CREATE TABLE IF NOT EXISTS `contour` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `category_id` varchar(36) NOT NULL,
  `selection_id` varchar(36) DEFAULT NULL,
  `reference_contour_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_contour_category` (`category_id`),
  KEY `fk_contour_selection` (`selection_id`),
  KEY `fk_contour_ref_contour` (`reference_contour_id`),
  CONSTRAINT `fk_contour_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`),
  CONSTRAINT `fk_contour_selection` FOREIGN KEY (`selection_id`) REFERENCES `selection` (`id`),
  CONSTRAINT `fk_contour_ref_contour` FOREIGN KEY (`reference_contour_id`) REFERENCES `reference_contour` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
