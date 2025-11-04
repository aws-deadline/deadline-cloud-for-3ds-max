## 0.1.7 (2025-11-04)


### Features
* **render elements**: VRay split frame buffer and VFB fixes to support Render Elements (#167) ([`38356fa`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/38356fa07e0de4fbaf3fd047cf2c3e9ff985de31))
* **render elements**: Adapter support for render elements. Apply settings from job template via pyxms (#162) ([`c0d7ab2`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/c0d7ab2eb5f91857e9bdcbe386da9bdd11e8294a))
* Add new shared utilities class to support render element and general interaction with pyxms (#160) ([`cc2a1fe`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/cc2a1fe5f15f696f884a0461ed9c7fba0a3e8514))

### Bug Fixes
* Do not add render elements to init param if no render elements e… (#170) ([`e0024fe`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/e0024fef4fed3d2290a5622b7888a492e4354181))
* Add sticky settings for various job settings (#165) ([`50520b1`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/50520b1afa7b46897a1c0ae22e73579e8d204b62))
* Fix V_Ray renderer generally using "starts with" ([`872f453`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/872f45395eb2f180bfd4c41f595fb3e734fae6e4))

## 0.1.6 (2025-09-05)



### Bug Fixes
* add Constants to support VRay7 GPU (#132) ([`ceb2463`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/ceb24631c9a1b9da8d39390a634618c29b907d82))
* use correct VRay regex in adaptor init-data schema (#136) ([`ae23570`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/ae23570d6c52a9fe07b920caedf59b0785b08cd6))

## 0.1.5 (2025-07-02)


### Features
* Implement 3dsMax submitter installer (#110) ([`bbcba95`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/bbcba9589b1aad162957b21f4c0bcbf406ed2093))
* Add submitter support for 3dsMax 2025+ (#109) ([`f33b4e0`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/f33b4e0583b983ad7b4460206b7e051f668217f8))
* Add V-Ray 7 support without GPU (#104) ([`48d3eeb`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/48d3eeb05d90d2a93b28f5d7d083c1fb01d19ce6))


## 0.1.4 (2025-03-21)



### Bug Fixes
* Add length validations for job settings input fields (#86) ([`9dc4d50`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/9dc4d50993443fa5d3f4a5fd653454aaf4eaef4b))
* Add length valdation for QLineEdit widgets (#84) ([`26222ea`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/26222ea3987f69b5a30a58efe40fd0e9922bdaa7))

## 0.1.3 (2025-02-11)


### Features
* Added Support for Redshift Renderer (#68) ([`11684a5`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/11684a54867a1db29c5f4b8cd4a8fd297a3bd2d7))
* Add support for 3dsmaxbatch (#72) ([`04ec149`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/04ec1494f06b737ff05c57ce31a62cec8b77ad29))

### Bug Fixes
* fix typo in wheel name check during job submission (#71) ([`f5d42bd`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/f5d42bdf215bfcb0818788592e29c79de4f5a1e8))

## 0.1.2 (2024-12-12)


### Features
* Added Support for V-Ray 6 and V-Ray GPU 6 Renderers (#35) ([`8cea88e`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/8cea88ec48848c4f0324e5e63ba7d09dca5a2ac6))
* Added Support for Corona Renderer (#34) ([`ff3c26f`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/ff3c26f52783164b63dfdb6cd74603738d765f9c))

### Bug Fixes
* Run 3dsMax in silent mode (#52) ([`59d1716`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/59d1716000dda7fbf41a3b81888ded550f04a780))

## 0.1.1 (2024-05-01)

### Dependencies
* Update deadline requirement from ==0.47.* to ==0.48.* (#23) ([`b45f444`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/b45f444c91d5655c7c5b8278973a540a349c2b5e))


## 0.1.0 (2024-04-02)

### BREAKING CHANGES
* public release (#11) ([`55d4c2f`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/55d4c2fbeeb76f036466f1754d2b0a205251d939))



## v0.0.1 (2024-03-26)

### BREAKING CHANGES
* initial integeration commit (#2) ([`873d2de`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/873d2ded6d1dfe1f590e9e3460bd76266954efc0))


### Bug Fixes
* added some missing install files, updated development readme, added job bundle test scaffolding (#5) ([`48a0170`](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/commit/48a0170de5b738c3abe3d8d416c23c10fa4aa618))


