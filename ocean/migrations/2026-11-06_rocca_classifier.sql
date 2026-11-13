-- ROCCA whistle classifier tables (see ocean/app/classifier.py).

-- An uploaded PAMGuard ROCCA whistle classifier (.model file stored in the filespace).
CREATE TABLE IF NOT EXISTS `classifier` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `name` varchar(100) NOT NULL,
  `model_file_id` varchar(36) NOT NULL,
  `species_list` text DEFAULT NULL,
  `num_stages` int(4) DEFAULT NULL,
  `threshold` int(4) NOT NULL DEFAULT 40,
  `strong_diff` tinyint(1) NOT NULL DEFAULT 0,
  `updated_by_id` varchar(36) DEFAULT NULL,
  `created_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `classifier_name` (`name`),
  CONSTRAINT `fk_classifier_model_file_id` FOREIGN KEY (`model_file_id`) REFERENCES `file` (`id`),
  CONSTRAINT `fk_classifier_updated_by_id` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- The classifier used for an encounter's selections (none if NULL).
ALTER TABLE `encounter`
  ADD COLUMN IF NOT EXISTS `classifier_id` varchar(36) DEFAULT NULL,
  ADD FOREIGN KEY IF NOT EXISTS `fk_encounter_classifier_id` (`classifier_id`) REFERENCES `classifier` (`id`);

-- The result of running one classifier on one selection. `stage_votes` holds the raw votes
-- of every classifier stage (JSON) so `classified_as` can be recomputed when the threshold
-- changes. `stats_hash` is a hash of the contour statistics the classifier was given, used
-- to detect results that are out of date.
CREATE TABLE IF NOT EXISTS `selection_classification` (
  `id` varchar(36) NOT NULL DEFAULT uuid(),
  `selection_id` varchar(36) NOT NULL,
  `classifier_id` varchar(36) NOT NULL,
  `classified_as` varchar(50) NOT NULL,
  `stage_votes` text DEFAULT NULL,
  `error` varchar(255) DEFAULT NULL,
  `stats_hash` char(40) DEFAULT NULL,
  `updated_datetime` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `selection_classifier` (`selection_id`, `classifier_id`),
  CONSTRAINT `fk_selection_classification_selection_id` FOREIGN KEY (`selection_id`) REFERENCES `selection` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_selection_classification_classifier_id` FOREIGN KEY (`classifier_id`) REFERENCES `classifier` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
