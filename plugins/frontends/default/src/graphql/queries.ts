import { gqlTag as gql } from "shenas-frontends";

// --- App Shell ---
export const GET_HOTKEYS = gql`
  {
    hotkeys
  }
`;

export const GET_WORKSPACE = gql`
  {
    workspace
  }
`;

export const GET_DASHBOARDS = gql`
  {
    dashboards {
      name
      displayName
      tag
      js
      description
    }
  }
`;

export const GET_PLUGIN_KINDS = gql`
  {
    pluginKinds
  }
`;

// --- Dynamic query builders (depend on discovered pluginKinds) ---
// These build a DocumentNode from a runtime string. Apollo's gql tag only
// accepts DocumentNode fragments as interpolation values, so we call it with
// a single-element TemplateStringsArray containing the already-assembled query.

const PLUGIN_FIELDS = `name displayName enabled syncedAt hasAuth isAuthenticated`;

function dynamicGql(query: string) {
  return gql(Object.assign([query], { raw: [query] }) as unknown as TemplateStringsArray);
}

export function buildAppDataQuery(kinds: { id: string }[]) {
  const kindQueries = kinds.map(({ id }) => `p_${id}: plugins(kind: "${id}") { ${PLUGIN_FIELDS} }`).join("\n    ");
  return dynamicGql(`{
    dashboards { name displayName tag js description }
    hotkeys
    workspace
    dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } }
    ${kindQueries}
    theme { css }
    deviceName
    schemaPlugins
  }`);
}

export function buildPluginStatsQuery(kinds: { id: string }[]) {
  const kindQueries = kinds
    .map(
      ({ id }) =>
        `p_${id}: plugins(kind: "${id}") { name displayName package version enabled description syncedAt hasAuth isAuthenticated }`,
    )
    .join("\n    ");
  return dynamicGql(`{ ${kindQueries} dbStatus { schemas { name tables { name rows earliest latest } } } }`);
}

export const GET_PLUGIN_INFO = gql`
  query GetPluginInfo($kind: String!, $name: String!) {
    pluginInfo(kind: $kind, name: $name)
  }
`;

export const GET_PLUGIN_INFO_WITH_TRANSFORMS = gql`
  query GetPluginInfoWithTransforms($kind: String!, $name: String!) {
    pluginInfo(kind: $kind, name: $name)
    transforms {
      id
      source {
        id
        schemaName
        tableName
      }
      target {
        id
        schemaName
        tableName
      }
      sourcePlugin
      description
      enabled
    }
  }
`;

export const GET_TABLE_COLUMN_INFO = gql`
  query GetTableColumnInfo($s: String!, $t: String!) {
    tableColumnInfo(schema: $s, table: $t) {
      name
      dbType
      description
      unit
      nullable
      valueRange
      exampleValue
      interpretation
    }
  }
`;

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
  }
`;

export const GET_TRANSFORM_TYPES = gql`
  {
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

export const GET_CREATE_TRANSFORM_DATA = gql`
  {
    dbTables
    schemaTables
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
  query GetAuthFields($pipe: String!) {
    authFields(pipe: $pipe) {
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
export const GET_FLOW_DATA = gql`
  {
    transforms {
      id
      transformType
      source {
        id
        schemaName
        tableName
      }
      target {
        id
        schemaName
        tableName
      }
      sourcePlugin
      enabled
    }
    dependencies {
      source
      targets
    }
  }
`;

export const GET_SOURCE_ENTITIES = gql`
  query GetSourceEntities($plugin: String!) {
    sourceEntitiesForPlugin(plugin: $plugin) {
      uuid
      type
      name
      description
      status
    }
  }
`;

export const GET_SOURCE_MAPPABLE_ITEMS = gql`
  query GetSourceMappableItems($plugin: String!) {
    sourceMappableItemsForPlugin(plugin: $plugin) {
      sourceTable
      sourceRowKey
      name
      description
      suggestedType
      mappedToUuid
      mappedToName
      mappedToType
    }
  }
`;
