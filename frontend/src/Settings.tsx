import type { InvenTreePluginContext } from '@inventreedb/ui';
import { Alert, Button, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';

type SettingsContext = {
  oauth_authorize_url?: string;
  client_id?: string;
  redirect_uri?: string;
  docs_url?: string;
  base_url_state?: string;
  base_url_message?: string;
};

function statusBadge(state: string | undefined, message: string | undefined) {
  const ok = state === 'ok';

  return (
    <Text span fw={700} c={ok ? 'green' : 'red'}>
      {message || 'Unknown'}
    </Text>
  );
}

function buildAuthorizeUrl(context: SettingsContext): string {
  const base =
    context.oauth_authorize_url ||
    'https://api.digikey.com/v1/oauth2/authorize';

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: context.client_id || '',
    redirect_uri: context.redirect_uri || ''
  });

  return `${base}?${params.toString()}`;
}

function normalizeContext(data: InvenTreePluginContext): SettingsContext {
  const outer = data?.context as
    | SettingsContext
    | { context?: SettingsContext }
    | undefined;

  if (outer && 'context' in outer && outer.context) {
    return outer.context;
  }

  return (outer as SettingsContext) || {};
}

function PluginSettingsDisplay({
  context
}: {
  context: InvenTreePluginContext;
}) {
  const settingsContext = normalizeContext(context);
  const docsUrl =
    settingsContext.docs_url ||
    'https://github.com/SergeoLacruz/inventree-supplier-panel';
  const authorizeUrl = buildAuthorizeUrl(settingsContext);
  const canCreateToken =
    Boolean(settingsContext.client_id) && Boolean(settingsContext.redirect_uri);

  return (
    <Alert color='blue' title='Setup'>
      <p>
        <b>Setup</b>
      </p>
      <ol>
        <li>
          Read the{' '}
          <a href={docsUrl} target='_blank' rel='noopener noreferrer'>
            documentation on GitHub
          </a>
        </li>
        <li>Enable the plugin</li>
        <li>Put all required keys into settings</li>
        <li>Create the Digikey token</li>
        <li>
          Remove shopping carts and lists regularly from your supplier accounts
        </li>
      </ol>
      <p>
        <b>Status</b>
      </p>
      <table>
        <tbody>
          <tr>
            <td>Server Base URL</td>
            <td>
              {statusBadge(
                settingsContext.base_url_state,
                settingsContext.base_url_message
              )}
            </td>
          </tr>
          <tr>
            <td>Callback URL (add this to your Digikey account)</td>
            <td>{settingsContext.redirect_uri || 'Not available'}</td>
          </tr>
        </tbody>
      </table>
      <Button
        color='blue'
        disabled={!canCreateToken}
        onClick={() => {
          notifications.show({
            title: 'Digikey OAuth',
            message: 'Opening Digikey authorization page in a popup window.',
            color: 'blue'
          });

          window.open(
            authorizeUrl,
            'suppliercart_digikey_oauth',
            'width=1000,height=800'
          );
        }}
      >
        Create Digikey Token
      </Button>
    </Alert>
  );
}

export function RenderPluginSettings(context: InvenTreePluginContext) {
  return <PluginSettingsDisplay context={context} />;
}
