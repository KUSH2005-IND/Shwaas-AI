window.config = {
  routerBasename: '/clinical/pacs/viewer',
  showStudyList: false,
  extensions: [],
  modes: [],
  dataSources: [{
    namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
    sourceName: 'dicomweb',
    configuration: {
      friendlyName: 'ShwaasAI private imaging', name: 'Orthanc',
      wadoUriRoot: '/clinical/pacs/dicom-web',
      qidoRoot: '/clinical/pacs/dicom-web',
      wadoRoot: '/clinical/pacs/dicom-web',
      qidoSupportsIncludeField: true,
      imageRendering: 'wadors', thumbnailRendering: 'wadors',
      enableStudyLazyLoad: true,
      supportsFuzzyMatching: false, supportsWildcard: false,
      dicomUploadEnabled: false,
    },
  }],
  defaultDataSourceName: 'dicomweb',
};
