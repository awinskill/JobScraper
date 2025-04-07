CREATE TABLE [dbo].[LinkedInJobs] (
    [Id]           BIGINT  NOT NULL,
    [title]        TEXT NULL,
    [company]      TEXT NULL,
    [location]     TEXT NULL,
    [date]         DATE NULL,
    [salary]       TEXT NULL,
    [salary_lower] BIGINT  CONSTRAINT [DEFAULT_LinkedInJobs_salary_lower] DEFAULT ((0)) NULL,
    [salary_upper] BIGINT  CONSTRAINT [DEFAULT_LinkedInJobs_salary_upper] DEFAULT ((0)) NULL,
    [summary]      TEXT NULL,
    [description]  TEXT NULL,
    [url]          TEXT NULL,
    CONSTRAINT [PK_LinkedInJobs] PRIMARY KEY CLUSTERED ([Id] ASC)
);


GO

GRANT INSERT
    ON OBJECT::[dbo].[LinkedInJobs] TO [ApplicationUser]
    AS [dbo];


GO

GRANT SELECT
    ON OBJECT::[dbo].[LinkedInJobs] TO [ApplicationUser]
    AS [dbo];


GO

GRANT UPDATE
    ON OBJECT::[dbo].[LinkedInJobs] TO [ApplicationUser]
    AS [dbo];


GO

