CREATE TABLE `audit_events` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`action` text NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`detail` text DEFAULT '{}' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
--> statement-breakpoint
CREATE INDEX `audit_entity_idx` ON `audit_events` (`entity_type`,`entity_id`);--> statement-breakpoint
CREATE TABLE `candidates` (
	`id` text PRIMARY KEY NOT NULL,
	`job_id` text NOT NULL,
	`file_name` text NOT NULL,
	`file_hash` text NOT NULL,
	`name` text NOT NULL,
	`role` text DEFAULT '' NOT NULL,
	`company` text DEFAULT '' NOT NULL,
	`years` text DEFAULT '' NOT NULL,
	`city` text DEFAULT '' NOT NULL,
	`degree` text DEFAULT '' NOT NULL,
	`score` integer DEFAULT 0 NOT NULL,
	`status` text DEFAULT '待处理' NOT NULL,
	`skills` text DEFAULT '[]' NOT NULL,
	`strength` text DEFAULT '' NOT NULL,
	`risk` text DEFAULT '' NOT NULL,
	`summary` text DEFAULT '' NOT NULL,
	`dimensions` text DEFAULT '[]' NOT NULL,
	`provider` text DEFAULT 'rules' NOT NULL,
	`resume_excerpt` text DEFAULT '' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `candidates_job_hash_unique` ON `candidates` (`job_id`,`file_hash`);--> statement-breakpoint
CREATE INDEX `candidates_job_score_idx` ON `candidates` (`job_id`,`score`);--> statement-breakpoint
CREATE TABLE `jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`department` text DEFAULT '' NOT NULL,
	`location` text DEFAULT '' NOT NULL,
	`min_years` integer DEFAULT 0 NOT NULL,
	`must_have` text DEFAULT '[]' NOT NULL,
	`nice_to_have` text DEFAULT '[]' NOT NULL,
	`status` text DEFAULT 'open' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
