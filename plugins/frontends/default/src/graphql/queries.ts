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

// --- Plugins by kind ---
export const GET_PLUGINS_BY_KIND = gql`
  {
    sources: plugins(kind: "source") {
      name
      displayName
      enabled
      syncedAt
      hasAuth
      isAuthenticated
    }
    datasets: plugins(kind: "dataset") {
      name
      displayName
      enabled
    }
    dashboardPlugins: plugins(kind: "dashboard") {
      name
      displayName
      enabled
    }
    frontends: plugins(kind: "frontend") {
      name
      displayName
      enabled
    }
    themes: plugins(kind: "theme") {
      name
      displayName
      enabled
    }
    models: plugins(kind: "model") {
      name
      displayName
      enabled
    }
  }
`;

// --- DB Status ---
export const GET_DB_STATUS = gql`
  {
    dbStatus {
      keySource
      dbPath
      sizeMb
      schemas {
        name
        tables {
          name
          rows
          cols
          earliest
          latest
        }
      }
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
    dependencies {
      source
      targets
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
