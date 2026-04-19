import { gqlTag as gql } from "shenas-frontends";

// --- App Shell (single init query) ---
// Fetches everything the app shell needs in one round-trip: app config,
// db status, plugin lists for all kinds.
const PLUGIN_FIELDS = `name displayName enabled syncedAt hasAuth isAuthenticated tables totalRows`;
export const GET_APP_DATA = gql`
  {
    pluginKinds
    dashboards {
      name
      displayName
      tag
      js
      description
    }
    hotkeys
    workspace
    themeData: theme {
      css
    }
    deviceName
    source: plugins(kind: "source") { ${PLUGIN_FIELDS} }
    dataset: plugins(kind: "dataset") { ${PLUGIN_FIELDS} }
    dashboard: plugins(kind: "dashboard") { ${PLUGIN_FIELDS} }
    frontend: plugins(kind: "frontend") { ${PLUGIN_FIELDS} }
    theme: plugins(kind: "theme") { ${PLUGIN_FIELDS} }
    model: plugins(kind: "model") { ${PLUGIN_FIELDS} }
    transformer: plugins(kind: "transformer") { ${PLUGIN_FIELDS} }
    analysis: plugins(kind: "analysis") { ${PLUGIN_FIELDS} }
  }
`;

function dynamicGql(query: string) {
  return gql(Object.assign([query], { raw: [query] }) as unknown as TemplateStringsArray);
}

export { dynamicGql };

// --- Catalog ---
export const GET_DATA_RESOURCES = gql`
  {
    dataResources {
      id
      schemaName
      tableName
      displayName
      description
      plugin {
        name
        displayName
      }
      kind
      queryHint
      asOfMacro
      primaryKey
      columns {
        name
        dbType
        nullable
        description
        unit
      }
      timeColumns {
        timeAt
        timeStart
        timeEnd
      }
      freshness {
        lastRefreshed
        slaMinutes
        isStale
      }
      quality {
        expectedRowCountMin
        expectedRowCountMax
        actualRowCount
        latestChecks {
          checkType
          status
          message
          checkedAt
        }
      }
      userNotes
      tags
    }
  }
`;

export const GET_DATA_RESOURCE_DETAIL = gql`
  query GetDataResourceDetail($id: String!) {
    dataResource(resourceId: $id) {
      id
      schemaName
      tableName
      displayName
      description
      plugin {
        name
        displayName
      }
      kind
      queryHint
      asOfMacro
      primaryKey
      columns {
        name
        dbType
        nullable
        description
        unit
      }
      timeColumns {
        timeAt
        timeStart
        timeEnd
      }
      freshness {
        lastRefreshed
        slaMinutes
        isStale
      }
      quality {
        expectedRowCountMin
        expectedRowCountMax
        actualRowCount
        latestChecks {
          checkType
          status
          message
          checkedAt
        }
      }
      userNotes
      tags
      upstreamTransforms {
        id
        transformType
        source {
          id
          displayName
        }
        description
      }
      downstreamTransforms {
        id
        transformType
        target {
          id
          displayName
        }
        description
      }
    }
  }
`;

// --- Entities ---
export const GET_ENTITIES_DATA = gql`
  {
    entities {
      uuid
      type
      name
      description
      status
      isMe
    }
    entityRelationships {
      fromUuid
      toUuid
      type
      description
    }
    entityTypes {
      name
      displayName
      description
      icon
      parent
      isAbstract
    }
    entityRelationshipTypes {
      name
      displayName
      inverseName
      isSymmetric
      domainTypes
      rangeTypes
    }
  }
`;

// --- Hypotheses ---
export const GET_HYPOTHESES = gql`
  {
    hypotheses {
      id
      question
      plan
      inputs
      interpretation
      model
      mode
      promotedTo
      createdAt
      recipeJson
      resultJson
    }
  }
`;

export const GET_ANALYSIS_MODES = gql`
  {
    analysisModes
  }
`;

// --- Transforms ---
export const GET_TRANSFORMS = gql`
  query GetTransforms($source: String) {
    transforms(source: $source) {
      id
      transformType
      source {
        id
        schemaName
        tableName
        displayName
      }
      target {
        id
        schemaName
        tableName
        displayName
      }
      sourcePlugin
      params
      description
      isDefault
      enabled
      sql
    }
    dependencies {
      source
      targets
    }
    transformTypes {
      name
      displayName
      description
      paramSchema {
        name
        label
        type
        required
        description
        default
        options
      }
    }
  }
`;

export const GET_TABLE_COLUMNS = gql`
  query GetTableColumns($s: String!, $t: String!) {
    tableColumns(schema: $s, table: $t)
  }
`;

// --- Plugin Detail ---
// Note: pluginInfo query is dynamic (built per kind), keep as string builder
export const GET_THEME = gql`
  {
    theme {
      css
    }
  }
`;

export const GET_SUGGESTED_DATASETS = gql`
  query GetSuggestedDatasets($source: String) {
    suggestedDatasets(source: $source) {
      name
      title
      grain
      tableName
    }
  }
`;

// --- Categories ---
export const GET_CATEGORY_SETS = gql`
  {
    categorySets {
      id
      displayName
      description
      values {
        value
        sortOrder
        color
      }
    }
  }
`;

// --- Config ---
export const GET_PLUGIN_CONFIG = gql`
  query GetPluginConfig($kind: String!) {
    plugins(kind: $kind) {
      name
      hasConfig
      configEntries {
        key
        label
        value
        description
      }
    }
  }
`;

// --- Auth ---
export const GET_AUTH_FIELDS = gql`
  query GetAuthFields($source: String!) {
    authFields(source: $source) {
      fields {
        name
        prompt
        hide
      }
      instructions
      stored
    }
  }
`;

// --- Available Plugins ---
export const GET_AVAILABLE_PLUGINS = gql`
  query GetAvailablePlugins($kind: String!) {
    availablePlugins(kind: $kind)
  }
`;

// --- Flow ---
export const GET_SOURCE_ENTITIES = gql`
  query GetSourceEntities($plugin: String!) {
    sourceEntitiesForPlugin(plugin: $plugin) {
      uuid
      type
      name
      description
      status
    }
    entityTypes {
      name
      displayName
      isAbstract
      parent
    }
  }
`;

export const GET_ENTITY_WITH_STATEMENTS = gql`
  query GetEntityWithStatements($uuid: String!) {
    entity(uuid: $uuid) {
      uuid
      type
      name
      description
      status
      statements {
        entityId
        propertyId
        value
        valueLabel
        rank
        qualifiers
        source
        propertyLabel
        datatype
      }
    }
  }
`;
