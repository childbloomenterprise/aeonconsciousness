CREATE TABLE `artifacts` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`job_id` text NOT NULL,
	`path` text NOT NULL,
	`object_key` text NOT NULL,
	`size` integer NOT NULL,
	`sha256` text NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`job_id`) REFERENCES `jobs`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `artifact_path` ON `artifacts` (`job_id`,`path`);--> statement-breakpoint
CREATE INDEX `artifact_org` ON `artifacts` (`org_id`,`job_id`);--> statement-breakpoint
CREATE TABLE `audit` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`org_id` text NOT NULL,
	`actor` text NOT NULL,
	`action` text NOT NULL,
	`target` text NOT NULL,
	`detail` text NOT NULL,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `audit_org` ON `audit` (`org_id`,`id`);--> statement-breakpoint
CREATE TABLE `invitations` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`email` text NOT NULL,
	`role` text NOT NULL,
	`token_hash` text NOT NULL,
	`expires_at` integer NOT NULL,
	`consumed_by` text,
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `invitation_token` ON `invitations` (`token_hash`);--> statement-breakpoint
CREATE TABLE `jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`title` text NOT NULL,
	`brief` text NOT NULL,
	`status` text NOT NULL,
	`kind` text NOT NULL,
	`grant` text NOT NULL,
	`max_tokens` integer NOT NULL,
	`max_steps` integer NOT NULL,
	`max_revisions` integer NOT NULL,
	`deadline_minutes` integer NOT NULL,
	`used_tokens` integer DEFAULT 0 NOT NULL,
	`created_by` text NOT NULL,
	`approved_by` text,
	`idempotency_key` text NOT NULL,
	`worker_id` text,
	`lease_hash` text,
	`lease_expires_at` integer,
	`attempts` integer DEFAULT 0 NOT NULL,
	`result` text,
	`progress` text,
	`resume_options` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`worker_id`) REFERENCES `workers`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `jobs_idempotency` ON `jobs` (`org_id`,`idempotency_key`);--> statement-breakpoint
CREATE INDEX `jobs_queue` ON `jobs` (`org_id`,`status`,`created_at`);--> statement-breakpoint
CREATE TABLE `memberships` (
	`org_id` text NOT NULL,
	`subject` text NOT NULL,
	`email` text NOT NULL,
	`role` text NOT NULL,
	`created_at` integer NOT NULL,
	PRIMARY KEY(`org_id`, `subject`),
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `organizations` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`owner_subject` text,
	`daily_jobs` integer DEFAULT 25 NOT NULL,
	`daily_tokens` integer DEFAULT 1000000 NOT NULL,
	`max_task_tokens` integer DEFAULT 50000 NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `workers` (
	`id` text PRIMARY KEY NOT NULL,
	`org_id` text NOT NULL,
	`name` text NOT NULL,
	`token_hash` text NOT NULL,
	`mode` text NOT NULL,
	`revoked` integer DEFAULT 0 NOT NULL,
	`heartbeat_at` integer,
	`created_at` integer NOT NULL,
	FOREIGN KEY (`org_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `workers_token` ON `workers` (`token_hash`);--> statement-breakpoint
CREATE INDEX `workers_org` ON `workers` (`org_id`);