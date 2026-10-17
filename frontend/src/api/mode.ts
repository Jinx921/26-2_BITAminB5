export function shouldUseMockApi(
  isProduction: boolean,
  mockEnabled: boolean,
): boolean {
  return !isProduction && mockEnabled
}
