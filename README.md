# Gut Analysis Toolbox

Development branch: [build, input limits and update boundaries](docs/fork-development.md). Published preview 3 remains unchanged.

## Corrective Apple Silicon test preview 3

[Preview 3 and the unchanged original comparison package](https://github.com/justinvassantachart/GutAnalysisToolbox/releases/tag/apple-silicon-preview-3)
are available for native arm64 Fiji on macOS 14+. Start with the
[complete bare-Mac instructions](docs/M1-CHATGPT-HANDOFF.md), including the
bundled-Java Fiji setup, model/engine installation, general kit 2.1 and new
multiplex manual fixtures. No developer tools are needed to use the packages.

**Do not use preview 2 multiplex exports for quantitative work.** Its
pre-existing result/landmark-handling defect left later-round channels
unaligned and reset calibration. Preview 3 fixes that path, with independently
verified saved TIFFs/ROIs from unchanged native SIFT and forced-MOPS acceptance
tests. [Before/after multiplex evidence](native-inference/validation/multiplex-full/results/mac-ab046cb/README.md).
Older release bytes remain unchanged.

This branch supplies isolated native neuron/subtype inference and Template
Matching, plus verified result-handling fixes. The
[40-image native-Mac report](native-inference/validation/mac-corpus/results/mac-9b599df/REPORT.md)
preserves equal counts/centers and the small mask/outline differences; these
are runtime-consistency checks rather than biological ground truth.
See the [workflow matrix and remaining limitations](docs/apple-silicon-workflow-matrix.md).
Physical GPU/OpenCL access and complete interactive workflows remain to be tested;
this is not an all-workflow or all-M-series support claim. Existing Intel
installations keep their legacy inference backend. Clone this feature branch
explicitly; the unchanged default `main` does not contain these changes:

```sh
git clone --branch feat/apple-silicon-stardist https://github.com/justinvassantachart/GutAnalysisToolbox.git
```

For the immutable tested package source, use tag `apple-silicon-preview-3`
(`bb897c237732cf8569a1515eb8d7ed69feb2ab31`). No upstream pull request has been opened.

[![DOI:10.1101/2024.01.17.576140](http://img.shields.io/badge/DOI-10.1101/2024.01.17.576140-B31B1B.svg)](https://doi.org/10.1242/jcs.261950)


**To get started with using GAT, please go to the** [**Documentation**](https://gut-analysis-toolbox.gitbook.io/docs/).

***********
<p align="center">
<img src="https://github.com/pr4deepr/GutAnalysisToolbox/blob/main/wiki_images/figures/gat_summary_fig.png" alt="GAT_overview" width="700" >
</p>

Gut Analysis Toolbox or GAT allows the semi-automated analysis of the cells within the enteric nervous system of the gastrointestinal tract in **2D**. GAT enables quantification of enteric neurons and their subtypes in **gut wholemounts**. It can run in FIJI or QuPath, popular image analysis softwares in microscopy and uses deep learning models to segment cells of interest. 

The workflows are available as video tutorials on [Youtube in two separate playlists for Fiji and QuPath](https://www.youtube.com/channel/UC03y9hDwDsVAhgeebyWpoew/playlists).


What you can do with GAT:
* Semi-automated analysis of number of enteric neurons: Uses pan-neuronal marker Hu or anything with similar 
 labelling
* Normalise counts to the number of ganglia.
* Count number of neuronal subtypes, such as ChAT, nNOS etc..
* Spatial analysis using number of neighboring cells.
* Calcium imaging analysis: Alignment of images and extraction of normalised traces (Fiji)


## Reporting problems

If you have any difficulties, suggestions or find any bugs, you can either:

* Use [this link](https://forms.gle/oEpFMtQo29Dr9AQT7) to access a Google form for submitting issues or questions.

OR

* Create a post under [Issues](https://github.com/pr4deepr/GutAnalysisToolbox/issues) 

OR

* Post the problem on the [Imagesc forum](https://forum.image.sc/) and tag @pr4deepr


## Installing and configuring GAT in Fiji

Click  on this video to watch how to install and configure FIJI and GAT

[![Youtube](https://img.youtube.com/vi/GmE_lz-m0Rg/0.jpg)](https://www.youtube.com/playlist?list=PLmBt1Dumq60p4mIFT4j7TP_PVRjbO55Oi)

Once installed, launch GAT from the Fiji menu: **GATV2 › Start GAT**. On first
launch GAT runs an environment check (models, DeepImageJ engines, required
plugins) and tells you which update sites, if any, still need to be enabled.

GAT requires the following update sites (enable them under
*Help › Update… › Manage update sites*):

* 3D ImageJ Suite
* BIG-EPFL
* CSBDeep
* clij
* clij2
* DeepImageJ
* Gut Analysis Toolbox
* IJPB-plugins (MorphoLibJ)
* StarDist
* PTBIOP

GAT update site: https://sites.imagej.net/GutAnalysisToolbox/

**Calcium imaging only:** the calcium imaging alignment uses the Template
Matching plugin, which is not in Fiji's list of update sites and must be added
manually. In *Manage update sites* click **Add unlisted site** and enter:

`https://sites.imagej.net/Template_Matching/`

***********

## Model files for use in FIJI

The GAT models are located in `Fiji.app/models` folder and contains 3 separate model files:

- **Enteric neuron model: 2D_enteric_neuron_v4_1.zip**
  
  StarDist model to segment enteric neurons labelled with Hu, a pan-neuronal marker
- **Enteric neuron subtype model: 2D_enteric_neuron_subtype_v4.zip**
  
  StarDist model to segment enteric neuronal subtypes. It has been trained on images with labelling for:
  * neuronal nitric oxide synthase (nNOS)
  * Calbindin
  * Calretinin
  * Mu-opioid receptor (MOR) reporter (mCherry)
  * Delta-opioid receptor (DOR) reporter (GFP)
  * Choline acetyltransferase (ChAT)
  * Neurofilament (NFM)
- **Ganglia model folder: 2D_Ganglia_RGB_v3.bioimage.io.model**
  
  DeepImageJ-based UNet model to segment ganglia. Needs both Hu and a neuronal/glial marker labelling the ganglia

### Model files for use in QuPath

[Click to Download QuPath model and scripts](https://wehieduau-my.sharepoint.com/:u:/g/personal/rajasekhar_p_wehi_edu_au/EdYxRodrJLNJj4wK77erHA0BfVKDJpOktgWQ3iIyLaUU1g?download=1)

Check here for more detail on using [QuPath models](https://github.com/pr4deepr/GutAnalysisToolbox/wiki/4.-QuPath-for-analysing-ENS)

**********************

### Accessing training data

To download the training data, notebooks and associated models please go to the following Zenodo link:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6096664.svg)](https://doi.org/10.5281/zenodo.6096664)

**********************
## Citing

[Sorensen L, Humenick A, Poon SSB, Han MN, Mahdavian NS, Rowe MC, Hamnett R, Gómez-de-Mariscal E, Neckel PH, Saito A, Mutunduwe K, Glennan C, Haase R, McQuade RM, Foong JPP, Brookes SJH, Kaltschmidt JA, Muñoz-Barrutia A, King SK, Veldhuis NA, Carbone SE, Poole DP, Rajasekhar P. Gut Analysis Toolbox: Automating quantitative analysis of enteric neurons. J Cell Sci. 2024 Sep 2:jcs.261950. doi: 10.1242/jcs.261950.](https://doi.org/10.1242/jcs.261950)
