import { ApolloClient, InMemoryCache, HttpLink, gql } from "@apollo/client/core";

export { gql };

let _client: ApolloClient<unknown> | null = null;

/**
 * Return the shared Apollo Client singleton.
 *
 * The first call creates the client; subsequent calls return the same instance.
 * Session headers are injected by the patched global ``fetch()`` in app-shell,
 * so no custom link middleware is needed here.
 */
export function getClient(apiBase: string = "/api"): ApolloClient<unknown> {
  if (_client) return _client;
  _client = new ApolloClient({
    link: new HttpLink({ uri: `${apiBase}/graphql` }),
    cache: new InMemoryCache(),
    defaultOptions: {
      watchQuery: { fetchPolicy: "cache-and-network" },
      query: { fetchPolicy: "cache-first" },
    },
  });
  return _client;
}
