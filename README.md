# cbm3_to_sit

![](coverage.svg)

`cbm3_to_sit` processes any cbm-cfs3 project and extracts the core information required to run CBM.

## Features

* compare parameters stored in cbm-cfs3 projects versus those associated in default database (AIDB) and indicate any differences specifically
* extract disturbance events either from `tblDisturbanceEvents` or the CBM3 `predistage` output
* create an output with the core cbm-cfs3 project level information without the complicated SPUGroup, Scenario system, and default parameters that are built into the CBM-CFS3 ms access project database format.
* perform general validation on the data being processed and create detailed output which illustrates any issues found
* NFCMARs specific functionality:
  * extract PSPUID (if any) for each inventory record
  * extract spu groups and spu group membership by disturbance class (Fire, Harvest, ...)

## Inputs

* a cbm-cfs3 project database
* path to the corresponding cbm-cfs3 run directory (ie. `temp/CBMRun`)
* boolean flag indicating whether or not the project is an NFCMars project
* default parameters database
* boolean flag indicating whether to derive disturbance events from tblDisturbanceEvents (the default setting) and related tables or from predistage.csv output


## Outputs

* a collection of output tables stored as pandas dataframes.
* an output table indicating specifically where parameters differ between the specified default parmaeters database and the specified cbm3-project database.
* an output table indicating specifically where validation issues have been detected in the specified input

The following section outlines in detail the output tables

### metadata tables

* admin_boundary
* eco_boundary
* spatial_unit
* species
* disturbance_type

### classifiers

* `classifiers` project level classifier ids, names, value
* `classifier_values` classifier value ids, value names, value descriptions
* `classifier_set` classifier set ids: several tables have foreign keys
* `classifier_set_values` classifier set value ids, classifier set members

### inventory


| Column                        | Description                                                  |
| ----------------------------- | ------------------------------------------------------------ |
| id                            | primary key                                                  |
| default_spuid                 | aka RU, corresponds to tblSPUDefault                         |
| pspuid                        | nullable polygon id in NFCMARs spatial framework             |
| spuid                         | project-level spuid                                          |
| fire_spugroup_id              | spugroup id for fire events                                  |
| harvest_spugroup_id           | spugroup id for harvest                                      |
| deforestation_spugroup_id     | spugroup id for deforestation                                |
| insect_spugroup_id            | spugroup id for insects                                      |
| classifier_set_id             | foreign key to table `classifier_sets`                       |
| age                           | age [years]                                                  |
| area                          | area [hectares]                                              |
| delay                         | delay spinup parameter [years]                               |
| landclass                     | unfccc land class code foreign key to unfccc_land_class      |
| historic_disturbance_type_id  | historic disturbance type spinup parameter, foreign key to disturbance_types |
| last_pass_disturbance_type_id | historic disturbance type spinup parameter, foreign key to disturbance_types |

### disturbance_event

In this table the classifier/metatdata columns (cols 2 - 10 inclusive) are used as factors for disturbance eligibility.  If defined these columns are used as an additional factor to deem stands in the current simulation eligible or ineligible for disturbance.

| column # | Column                     | Description                                                  |
| -------- | -------------------------- | ------------------------------------------------------------ |
| 1        | id                         | primary key "disturbance event id"                           |
| 2        | default_spuid              | **nullable** aka RU, corresponds to tblSPUDefault            |
| 3        | pspuid                     | **nullable** polygon id in NFCMARs spatial framework         |
| 4        | spuid                      | **nullable** project-level spuid                             |
| 5        | fire_spugroup_id           | **nullable** spugroup id for fire events                     |
| 6        | harvest_spugroup_id        | **nullable** spugroup id for harvest                         |
| 7        | deforestation_spugroup_id  | **nullable** spugroup id for deforestation                   |
| 8        | insect_spugroup_id         | **nullable** spugroup id for insects                         |
| 9        | classifier_set_id          | **nullable** foreign key to table `classifier_sets`          |
| 10       | disturbance_eligibility_id | **nullable** foreign key to `disturbance_event_eligibility`  |
| 11       | efficiency                 | CBM efficiency parameter [proportion 0<x<=1]                 |
| 12       | sort_type_id               | CBM sort type parameter foreign key to `sort_type`           |
| 13       | target_type_id             | CBM target type parameter foreign key to `target_type`       |
| 14       | target                     | CBM target parameter in `target_type` units                  |
| 15       | disturbance_type_id        | CBM disturbance type parameter, foreign key to disturbance_types |
| 16       | disturbance_timestep       | CBM timestep parameter                                       |



### disturbance_event_eligibility

See **appendix** eligibility expressions topic for implementation details

| column                  | description                            |
| ----------------------- | -------------------------------------- |
| id                      | disturbance event eligibility id       |
| name                    | description of eligibility expressions |
| pool_filter_expression  | string expression                      |
| state_filter_expression | string expression                      |



### merch_volume

In this table the classifier/metatdata columns (cols 2 - 10 inclusive) are used to match merchantable volume yields with stands in the current simulation state.  The matching stand's spatial unit is used along with the species ids values to convert the merch volume to biomass/biomass Carbon increment.

If multiple stand-yield matches occur:

* the match with the larger number of defined metadata columns will be used
* in the event of a tie, the first lexicographically sorted match is used

| Column                    | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| id                        | primary key "merch volume id"                        |
| default_spuid             | **nullable** aka RU, corresponds to tblSPUDefault    |
| pspuid                    | **nullable** polygon id in NFCMARs spatial framework |
| spuid                     | **nullable** project-level spuid                     |
| fire_spugroup_id          | **nullable** spugroup id for fire events             |
| harvest_spugroup_id       | **nullable** spugroup id for harvest                 |
| deforestation_spugroup_id | **nullable** spugroup id for deforestation           |
| insect_spugroup_id        | **nullable** spugroup id for insects                 |
| classifier_set_id         | **nullable** foreign key to table `classifier_sets`  |

### merch_volume_component

| column          | description                                 |
| --------------- | ------------------------------------------- |
| id              | merch volume component id                   |
| species_id      | foreign key to `species`                    |
| merch_volume_id | foreign key to `merch_volume`               |
| age             | age [years]                                 |
| volume          | merchantable volume [m<sup>3</sup>/hectare] |

### disturbance_rules

| column               | description                                         |
| -------------------- | --------------------------------------------------- |
| id                   | disturbance rule identifier                         |
| disturbance_class_id | references disturbance class in default parameters  |
| rule_tracking_type   | foreign key to disturbance_rule_tracking_type.id    |
| rule_type            | foreign key to disturbance_rule_type.id             |
| spuid                | foreign key to project level spuid                  |
| rule_value           | rule value CBM parameter, units depend on rule_type |

### disturbance_rule_tracking_type

| column | description                            |
| ------ | -------------------------------------- |
| id     | disturbance_rule_tracking_type id      |
| name   | name of disturbance_rule_tracking_type |



### disturbance_rule_type

| column | description                    |
| ------ | ------------------------------ |
| id     | disturbance_rules_type id      |
| name   | name of disturbance_rules_type |
