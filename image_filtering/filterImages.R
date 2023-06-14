## Meghan A. Balk
## meghan.balk@nhm.uio.no

## This code:
# 1) reduces image list to those with 30 magnification
# 2) removes non Steginoporella magnifica images
# 3) removes images known to be of poor quality

#### LOAD PACKAGES ----
require(stringr)
require(dplyr)
require(ggplot2)
require(reshape2)
require(lmodel2)
require(stringr)

#### LOAD DATA ----
bryo.meta <- read.table("image_merge_txt_usingfileName_DONE_17Apr2023.csv",
                          header = TRUE,
                          sep = ";")
img.rm <- read.table("low_quality_images.csv",
                     header = TRUE, 
                     sep = ";")
wrg.sp <- read.table("wrong_species.csv",
                     header = TRUE,
                     sep = ";")

#### CREATE LIST OF FILE NAMES ----
#READ ALL AND CREATE LIST

l.img <- list.files(path = "/media/voje-lab/bryozoa/imaging/Stegino_images/combined-jpg",
                    full.names = TRUE,
                    recursive = TRUE)

img.path <- unlist(l.img)
length(img.path) #1890

img.tr <- gsub(img.path,
               pattern = "/media/voje-lab/bryozoa/imaging/Stegino_images/combined-jpg/",
               replacement = "")

img.parse <- str_split(img.tr,
                       pattern = "/")

fileNames <- c()
for(i in 1:length(img.parse)){
  fileNames[i] <- img.parse[[i]]
}

imgName <- str_extract(fileNames,
                       pattern = "[^.]+")

img.list <- as.data.frame(cbind(fileNames, imgName))

#### CREATE LIST OF FILES TO REMOVE ----

img.rm.list <- str_extract(img.rm$file.name,
                           pattern = "[^.]+") #344

wr.sp.list <- str_extract(wrg.sp$file.name,
                          pattern = "[^.]+") #35

mag.rm.list <- bryo.meta$image[bryo.meta$Magnification != 30] #36

#### FILTER IMAGES ----

img.filter <- img.list[!(img.list$imgName %in% img.rm.list),] #1549

img.filter <- img.filter[!(img.filter$imgName %in% wr.sp.list),] #1515

img.filter <- img.filter[!(img.filter$imgName %in% mag.rm.list),] #1467

length(unique(img.filter$fileNames)) #1467

#### WRITE OUT FILTERED DF ----

write.csv(img.filter,
          "filteredImages.csv",
          row.names = FALSE)
