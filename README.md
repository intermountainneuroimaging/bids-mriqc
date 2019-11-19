# bids-mriqc
Gear that runs the MRIQC pipeline on BIDS-curated data.

MRIQC calculates [Image Quality Metrics (IQMs)](https://mriqc.readthedocs.io/en/stable/measures.html#module-mriqc.qc) and saves them as JSON files and in HTML reports.

This can run at the subject or session (participant) level.

Inputs do not need to be provided because the mriqc pipeline will examine
the BIDS formatted data directly.

Perhaps the best way to use this gear is to run it and then download the
results and examine them locally by opening the "group" html files in a
browser.  The group files have links to the individual file reports.

This will create a zip archive for each html file to allow easy
on-platform viewing: a click on the .zip file opens it an a new
browser tab.  Note that links in the html files will not work and
clicking on .html files directly will not display them properly.
