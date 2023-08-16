#credit:  modified from https://github.com/kassambara/ggpubr/blob/master/R/theme_pubr.R


theme_pubr_SA <- function(base_size = 7, base_family = "Arial",
                        border = FALSE, margin = TRUE,
                        legend = c("top", "bottom", "left", "right", "none"),
                        x.text.angle = 0)
{
  half_line <- base_size/2
  if(!is.numeric(legend)) legend <- match.arg(legend)
  if(x.text.angle > 5) xhjust <- 1 else xhjust <- NULL

  if(border){
    panel.border <- element_rect(fill = NA, colour = "black", size = 0.7)
    axis.line <- element_blank()
  }
  else{
    panel.border <- element_blank()
    axis.line = element_line(colour = "black", size = 0.5)
  }


  if(margin)
    plot.margin <- margin(half_line, half_line, half_line,
                          half_line)
  else plot.margin <- unit(c(0.5,0.3,0.3,0.3),"mm")

  .theme <- theme_bw(base_size = base_size, base_family = base_family) %+replace%
    theme(panel.border = panel.border,
          panel.grid.major = element_blank(),
          panel.grid.minor = element_blank(),
		  strip.background = element_blank(), strip.text = element_blank(),
          axis.line = axis.line, axis.text = element_text(color = "black"),
          legend.key = element_blank(),
          #strip.background = element_rect(fill = "#F2F2F2", colour = "black", size = 0.7),
          plot.margin = plot.margin,
          legend.position = legend,
          complete = TRUE)

  if(x.text.angle!=0)
    .theme <- .theme + theme(axis.text.x = element_text(angle = x.text.angle, hjust = xhjust))

  .theme
}