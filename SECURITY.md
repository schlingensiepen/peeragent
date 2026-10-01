# Security

peeragent launches other programs and writes files. Two parts of it
are worth a security report rather than a bug report:

- anything that makes the tool run a command, or write to a path, that
  the caller did not name - the launch prompt, the folder, the session
  name and the duplication paths all come from the caller and reach a
  subprocess or the filesystem;
- anything that puts content into a log file that a caller could not
  expect there. Logs hold the text of the launch prompt, the captured
  pane and absolute paths, and they are written under the user's own
  state directory with no special permissions.

## Reporting

Use GitHub's private vulnerability reporting on this repository
(**Security** -> **Report a vulnerability**). That keeps the report
out of public view while it is being looked at.

If private reporting is not available to you, open a normal issue that
describes the class of problem and says a private channel is needed,
and leave out anything that would work as a recipe. Do not put a
working exploit, a captured log or a real prompt into a public issue.

## What to expect

This is a pre-release maintained by one person in their own time.
There is no service level and no promise of a fix date. A report will
be read, and what is confirmed will be written into
[MATURITY.md](MATURITY.md) under the known limits whether or not it
has been fixed, so nobody relies on something that is known to be
broken.

## Supported versions

The newest version is the only one that gets fixes, and it is still a
pre-release. There are no backports to 0.1.0.
