options(repos = c(CRAN = "https://cloud.r-project.org"))
list.of.packages <- c("plyr", "tidyverse", "readxl", "ggpubr",
"rcompanion", "caret", "ggthemes", "gridExtra", "extrafont", "ggrepel", "stringr")
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages )
