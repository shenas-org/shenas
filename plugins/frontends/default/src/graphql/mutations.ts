import { gqlTag as gql } from "shenas-frontends";

// --- Plugins ---
export const ENABLE_PLUGIN = gql`
  mutation EnablePlugin($k: String!, $n: String!) {
    enablePlugin(kind: $k, name: $n) {
      ok
      message
    }
  }
`;

export const DISABLE_PLUGIN = gql`
  mutation DisablePlugin($k: String!, $n: String!) {
    disablePlugin(kind: $k, name: $n) {
      ok
      message
    }
  }
`;

// --- Transforms ---
export const RUN_SOURCE_TRANSFORMS = gql`
  mutation RunSourceTransforms($source: String!) {
    runSourceTransforms(source: $source) {
      name
      count
    }
  }
`;

export const SEED_TRANSFORMS = gql`
  mutation {
    seedTransforms {
      seeded
      count
    }
  }
`;

export const RUN_DATASET_TRANSFORMS = gql`
  mutation RunDatasetTransforms($dataset: String!) {
    runDatasetTransforms(dataset: $dataset) {
      name
      count
    }
  }
`;

export const CREATE_TRANSFORM = gql`
  mutation CreateTransform($input: TransformCreateInput!) {
    createTransform(transformInput: $input) {
      id
    }
  }
`;

export const UPDATE_TRANSFORM = gql`
  mutation UpdateTransform($id: Int!, $sql: String!) {
    updateTransform(transformId: $id, sql: $sql) {
      id
    }
  }
`;

export const DELETE_TRANSFORM = gql`
  mutation DeleteTransform($id: Int!) {
    deleteTransform(transformId: $id) {
      ok
      message
    }
  }
`;

export const ENABLE_TRANSFORM = gql`
  mutation EnableTransform($id: Int!) {
    enableTransform(transformId: $id) {
      id
      enabled
    }
  }
`;

export const DISABLE_TRANSFORM = gql`
  mutation DisableTransform($id: Int!) {
    disableTransform(transformId: $id) {
      id
      enabled
    }
  }
`;

export const TEST_TRANSFORM = gql`
  mutation TestTransform($id: Int!) {
    testTransform(transformId: $id, limit: 5)
  }
`;

// --- Workspace ---
export const SAVE_WORKSPACE = gql`
  mutation SaveWorkspace($data: JSON!) {
    saveWorkspace(data: $data) {
      ok
    }
  }
`;

// --- Literature ---
export const REFRESH_LITERATURE = gql`
  mutation {
    refreshLiterature
  }
`;

// --- Catalog ---
export const UPDATE_DATA_RESOURCE = gql`
  mutation UpdateDataResource($id: String!, $ann: DataResourceAnnotationInput!) {
    updateDataResource(resourceId: $id, annotation: $ann) {
      id
    }
  }
`;

export const RUN_QUALITY_CHECKS = gql`
  mutation RunQualityChecks($id: String) {
    runQualityChecks(resourceId: $id) {
      checkType
      status
      message
    }
  }
`;

// --- Entities ---
export const CREATE_ENTITY = gql`
  mutation CreateEntity($input: EntityCreateInput!) {
    createEntity(entityInput: $input) {
      uuid
      name
    }
  }
`;

export const UPDATE_ENTITY = gql`
  mutation UpdateEntity($uuid: String!, $input: EntityUpdateInput!) {
    updateEntity(uuid: $uuid, entityInput: $input) {
      uuid
    }
  }
`;

export const DELETE_ENTITY = gql`
  mutation DeleteEntity($uuid: String!) {
    deleteEntity(uuid: $uuid) {
      ok
    }
  }
`;

export const CREATE_ENTITY_RELATIONSHIP = gql`
  mutation CreateEntityRelationship($from: String!, $to: String!, $type: String!) {
    createEntityRelationship(fromUuid: $from, toUuid: $to, relationshipType: $type) {
      fromUuid
    }
  }
`;

export const DELETE_ENTITY_RELATIONSHIP = gql`
  mutation DeleteEntityRelationship($from: String!, $to: String!, $type: String!) {
    deleteEntityRelationship(fromUuid: $from, toUuid: $to, relationshipType: $type) {
      ok
    }
  }
`;

// --- Hypotheses ---
export const ASK_HYPOTHESIS = gql`
  mutation AskHypothesis($q: String!, $mode: String!) {
    askHypothesis(question: $q, mode: $mode)
  }
`;

export const PROMOTE_HYPOTHESIS = gql`
  mutation PromoteHypothesis($id: Int!, $name: String!) {
    promoteHypothesis(hypothesisId: $id, name: $name)
  }
`;

export const FORK_HYPOTHESIS = gql`
  mutation ForkHypothesis($id: Int!) {
    forkHypothesis(hypothesisId: $id)
  }
`;

// --- Hotkeys ---
export const SET_HOTKEY = gql`
  mutation SetHotkey($id: String!, $b: String!) {
    setHotkey(actionId: $id, binding: $b) {
      ok
    }
  }
`;

export const DELETE_HOTKEY = gql`
  mutation DeleteHotkey($id: String!) {
    deleteHotkey(actionId: $id) {
      ok
    }
  }
`;

export const RESET_HOTKEYS = gql`
  mutation {
    resetHotkeys {
      ok
    }
  }
`;

// --- Categories ---
export const CREATE_CATEGORY_SET = gql`
  mutation CreateCategorySet($id: String!, $name: String!, $desc: String!) {
    createCategorySet(setId: $id, displayName: $name, description: $desc) {
      id
      displayName
    }
  }
`;

export const UPDATE_CATEGORY_SET = gql`
  mutation UpdateCategorySet($id: String!, $name: String!, $desc: String!) {
    updateCategorySet(setId: $id, displayName: $name, description: $desc) {
      id
      displayName
    }
  }
`;

export const UPDATE_CATEGORY_VALUES = gql`
  mutation UpdateCategoryValues($id: String!, $values: String!) {
    updateCategoryValues(setId: $id, values: $values) {
      id
      displayName
    }
  }
`;

export const DELETE_CATEGORY_SET = gql`
  mutation DeleteCategorySet($id: String!) {
    deleteCategorySet(setId: $id) {
      ok
    }
  }
`;

// --- Config ---
export const SET_CONFIG = gql`
  mutation SetConfig($kind: String!, $name: String!, $key: String!, $value: String!) {
    setConfig(kind: $kind, name: $name, key: $key, value: $value) {
      ok
    }
  }
`;

// --- Auth ---
export const AUTHENTICATE = gql`
  mutation Authenticate($source: String!, $creds: JSON!, $callbackUrl: String) {
    authenticate(source: $source, credentials: $creds, callbackUrl: $callbackUrl) {
      ok
      message
      error
      needsMfa
      oauthUrl
      oauthRedirect
    }
  }
`;

// --- Schema ---
export const FLUSH_SCHEMA = gql`
  mutation FlushSchema($s: String!) {
    flushSchema(schemaPlugin: $s)
  }
`;

// --- Suggestions ---
export const SUGGEST_DATASETS = gql`
  mutation SuggestDatasets($source: String) {
    suggestDatasets(source: $source)
  }
`;

export const ACCEPT_DATASET_SUGGESTION = gql`
  mutation AcceptDatasetSuggestion($name: String!) {
    acceptDatasetSuggestion(name: $name) {
      ok
      message
    }
  }
`;

export const DISMISS_DATASET_SUGGESTION = gql`
  mutation DismissDatasetSuggestion($name: String!) {
    dismissDatasetSuggestion(name: $name) {
      ok
      message
    }
  }
`;

export const SET_ENTITY_STATUS = gql`
  mutation SetEntityStatus($uuid: String!, $status: String!) {
    setEntityStatus(uuid: $uuid, status: $status) {
      ok
      message
    }
  }
`;

export const CREATE_PROPERTY = gql`
  mutation CreateProperty($propertyInput: PropertyCreateInput!) {
    createProperty(propertyInput: $propertyInput) {
      id
      label
      datatype
      domainType
      source
      wikidataPid
    }
  }
`;

export const UPSERT_STATEMENT = gql`
  mutation UpsertStatement($statementInput: StatementUpsertInput!) {
    upsertStatement(statementInput: $statementInput) {
      entityId
      propertyId
      value
      valueLabel
      source
    }
  }
`;

export const DELETE_STATEMENT = gql`
  mutation DeleteStatement($entityId: String!, $propertyId: String!, $value: String!) {
    deleteStatement(entityId: $entityId, propertyId: $propertyId, value: $value) {
      ok
      message
    }
  }
`;
