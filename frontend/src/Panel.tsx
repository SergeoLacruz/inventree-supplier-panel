import {
  ApiEndpoints,
  apiUrl,
  checkPluginVersion,
  type InvenTreePluginContext,
  InvenTreeTable,
  LocalizedComponent,
  ModelType,
  RowEditAction,
  useTable
} from '@inventreedb/ui';
import {
  Accordion,
  Alert,
  Button,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useCallback, useMemo, useState } from 'react';
import { loadLocale } from './locales';

type CartItem = {
  IPN?: string;
  SKU?: string;
  QuantityRequested?: number | string;
  QuantityAvailable?: number | string;
  UnitPrice?: number | string;
  ExtendedPrice?: number | string;
  Error?: string;
};

type CartData = {
  CartItems?: CartItem[];
  cart_key?: string;
  cart_date?: string;
  ID?: string;
  currency_code?: string;
  MerchandiseTotal?: number | string;
  message?: string;
};

type PanelContext = {
  transfer_url?: string;
  cart?: CartData;
};

function formatNumber(value: number | string | undefined): string {
  const numberValue = Number(value);

  if (Number.isFinite(numberValue)) {
    return numberValue.toFixed(4);
  }

  return value != null ? String(value) : '';
}

function normalizeContext(data: InvenTreePluginContext): PanelContext {
  const outer = data?.context as
    | PanelContext
    | { context?: PanelContext }
    | undefined;

  if (outer && 'context' in outer && outer.context) {
    return outer.context;
  }

  return (outer as PanelContext) || {};
}

function statusForItem(item: CartItem): 'OK' | 'Not OK' {
  if (Number(item.QuantityRequested) < Number(item.QuantityAvailable)) {
    return 'OK';
  }

  return 'Not OK';
}

function cartStatusColor(message: string): 'green' | 'red' {
  return message === 'OK' ? 'green' : 'red';
}

function SupplierCartTable({ cartData }: { cartData?: CartData }) {
  if (
    !cartData ||
    !Array.isArray(cartData.CartItems) ||
    cartData.CartItems.length === 0
  ) {
    return <Text c='dimmed'>No cart data available.</Text>;
  }

  return (
    <div className='table-responsive'>
      <table className='table table-condensed'>
        <thead>
          <tr>
            <th>IPN</th>
            <th>SKU</th>
            <th>Required</th>
            <th>Available</th>
            <th>Status</th>
            <th style={{ textAlign: 'right' }}>Price</th>
            <th style={{ textAlign: 'right' }}>Total</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {cartData.CartItems.map((item, index) => (
            <tr key={`${item.IPN || item.SKU || 'item'}-${index}`}>
              <td>{item.IPN || ''}</td>
              <td>{item.SKU || ''}</td>
              <td>{item.QuantityRequested ?? ''}</td>
              <td>{item.QuantityAvailable ?? ''}</td>
              <td>
                <Text
                  c={statusForItem(item) === 'OK' ? 'green' : 'red'}
                  fw={700}
                >
                  {statusForItem(item)}
                </Text>
              </td>
              <td style={{ textAlign: 'right' }}>
                {formatNumber(item.UnitPrice)}
              </td>
              <td style={{ textAlign: 'right' }}>
                {formatNumber(item.ExtendedPrice)}
              </td>
              <td>{item.Error || ''}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td>
              <b>Total</b>
            </td>
            <td style={{ textAlign: 'right' }}>
              {cartData.currency_code || ''}
            </td>
            <td style={{ textAlign: 'right' }}>
              {formatNumber(cartData.MerchandiseTotal)}
            </td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function SupplierCartPanel({ context }: { context: InvenTreePluginContext }) {
  const panelContext = useMemo(() => normalizeContext(context), [context]);
  const orderId = useMemo(() => {
    return context.model === ModelType.purchaseorder
      ? context.id || null
      : null;
  }, [context.model, context.id]);

  const supportsTables = useMemo(() => !!context.tables, [context.tables]);
  const tableState = useTable('suppliercart-po-lines-table');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [resultMessage, setResultMessage] = useState<string>('Ready');
  const [cartData, setCartData] = useState<CartData | undefined>(
    panelContext.cart
  );

  const currentCartId = cartData?.ID || '';
  const cartBaseUrl = 'https://www.digikey.ch/de/mylists/list/';

  const transferCart = useCallback(async () => {
    if (!panelContext.transfer_url) {
      setResultMessage('Transfer URL is missing');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(panelContext.transfer_url, {
        method: 'GET',
        credentials: 'include'
      });

      const nextCartData = (await response.json()) as CartData;
      setResultMessage(nextCartData.message || 'Error');
      setCartData(nextCartData);
    } catch {
      setResultMessage('Request failed');
    } finally {
      setIsLoading(false);
    }
  }, [panelContext.transfer_url]);

  const openSupplierCart = useCallback(() => {
    if (!currentCartId) {
      return;
    }

    window.open(
      `${cartBaseUrl}${encodeURIComponent(currentCartId)}`,
      '_blank',
      'noopener,noreferrer'
    );
  }, [currentCartId]);

  return (
    <Accordion defaultValue='supplier-actions'>
      <Accordion.Item value='supplier-actions'>
        <Accordion.Control>
          <Title c={context.theme.primaryColor} order={4}>
            Supplier Cart Actions
          </Title>
        </Accordion.Control>
        <Accordion.Panel>
          <Stack gap='sm'>
            <Group gap='sm'>
              <Button color='dark' loading={isLoading} onClick={transferCart}>
                Transfer PO
              </Button>
              <Button
                color='dark'
                disabled={!currentCartId}
                onClick={openSupplierCart}
              >
                Open Supplier Cart
              </Button>
            </Group>

            <Alert
              color={cartStatusColor(resultMessage)}
              title='Transfer Result'
            >
              {resultMessage}
            </Alert>

            <SimpleGrid cols={2}>
              <Text>
                <b>Created supplier key:</b> {cartData?.cart_key || '-'}
              </Text>
              <Text>
                <b>Cart date:</b> {cartData?.cart_date || '-'}
              </Text>
            </SimpleGrid>

            <SupplierCartTable cartData={cartData} />
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value='po-lines'>
        <Accordion.Control>
          <Title c={context.theme.primaryColor} order={4}>
            Purchase Order Lines
          </Title>
        </Accordion.Control>
        <Accordion.Panel>
          {supportsTables && orderId ? (
            <InvenTreeTable
              url={apiUrl(ApiEndpoints.purchase_order_line_list)}
              tableState={tableState}
              context={context}
              props={{
                enableSelection: true,
                enablePagination: true,
                enableRefresh: true,
                modelType: ModelType.purchaseorderlineitem,
                params: {
                  order: orderId
                },
                rowActions: (record: any) => [
                  RowEditAction({
                    onClick: () => {
                      notifications.show({
                        title: 'PO line selected',
                        message: `Selected line for part ${record?.part_detail?.name || record?.part || '-'}`,
                        color: 'blue'
                      });
                    }
                  })
                ]
              }}
              columns={[
                {
                  accessor: 'line'
                },
                {
                  accessor: 'part'
                },
                {
                  accessor: 'quantity'
                },
                {
                  accessor: 'target_date'
                }
              ]}
            />
          ) : (
            <Alert color='red' title='Table Not Supported'>
              This version of InvenTree does not support tables within plugins.
            </Alert>
          )}
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}

export function renderSupplierCartPanel(context: InvenTreePluginContext) {
  checkPluginVersion(context);

  return (
    <LocalizedComponent
      i18n={context.i18n}
      locale={context.locale}
      loadLocale={loadLocale}
    >
      <SupplierCartPanel context={context} />
    </LocalizedComponent>
  );
}
