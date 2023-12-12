import * as dz from "@aws-sdk/client-datazone";
import { Logger } from '@aws-lambda-powertools/logger';

export interface HandlerEvent { }
export interface Context { }

const DOMAIN_ID = process.env.DATAZONE_DOMAIN_ID || ''
const PROJECT_ID = process.env.DATAZONE_PROJECT_ID || ''

const client = new dz.DataZone({ region: process.env.AWS_REGION || "eu-central-1" })


type InputEvent = {
    tableArn: string,
    metadata: {
        metadataFormId: string,
        values: {
            string: string
        }
    }
}

type Asset = {
    name: string,
    assetId: string,
    externalIdentifier: string,
    forms: dz.FormOutput[]
}

type FindAssetsOutput = {
    event: InputEvent,
    assets: Asset[] | undefined
}

type UpdateAssetMetadataFormEvent = {
    event: InputEvent,
    asset: Asset
}


const logger = new Logger({ serviceName: 'metadataUpdate', logLevel: 'debug' });



/**
 * Find Assets in DataZone Handler
 * and filter using tableArn input field
 * @param event 
 * @param context 
 * @returns 
 */
export const findAssetsHandler = async (event: InputEvent, context: Context): Promise<FindAssetsOutput> => {

    logger.debug('input event', { data: event })

    const results = await client.search({
        domainIdentifier: DOMAIN_ID,
        searchScope: "ASSET",
        owningProjectIdentifier: PROJECT_ID,
        additionalAttributes: ["FORMS"]
    })

    logger.debug('search API response', { data: results.items })

    return {
        event,
        assets: results.items
            ?.filter(item => item.assetItem?.externalIdentifier?.startsWith(event.tableArn + "." + PROJECT_ID))
            .map(item => ({
                "name": item.assetItem?.name!,
                "assetId": item.assetItem?.identifier!,
                "externalIdentifier": item.assetItem?.externalIdentifier!,
                "forms": item.assetItem?.additionalAttributes?.formsOutput!
            })) || undefined
    }
}





/**
 * Update asset metadata form with values provided in the Payload
 * @param event 
 * @param context 
 * @returns 
 */
export const updateAssetMetadataFormHandler = async (event: UpdateAssetMetadataFormEvent, context: Context) => {

    /**
     * Convert Forms Values to createAssetRevision -> FormInput
     */
    logger.debug('input event', { data: event })
    const convertedForms: dz.FormInput[] = event.asset?.forms.map(form => {
        let updatedContent: string | undefined;

        if (form.formName === event.event.metadata.metadataFormId) {
            updatedContent = JSON.stringify({
                ...JSON.parse(form.content!),
                ...event.event.metadata.values
            })
        }
        return {
            formName: form.formName,
            content: updatedContent || form.content,
            typeIdentifier: form.typeName,
            typeRevision: form.typeRevision
        }
    });
    logger.debug('convertedForms', { data: convertedForms })

    const response = await client.createAssetRevision({
        domainIdentifier: DOMAIN_ID,
        identifier: event.asset?.assetId,
        formsInput: convertedForms,
        name: event.asset.name,
    })
    logger.debug('createAssetRevision API response', { data: response })
    return event

}


/**
 * Publis the new Asset Revision in Datazone
 * @param event 
 * @param context 
 * @returns 
 */
export const publishAssetRevisionHandler = async (event: UpdateAssetMetadataFormEvent, context: Context) => {

    logger.debug('input event', { data: event })
    const response = await client.createListingChangeSet({
        action: "PUBLISH",
        domainIdentifier: DOMAIN_ID,
        entityIdentifier: event.asset?.assetId,
        entityType: "ASSET"
    })
    logger.debug('createListingChangeSet API response', { data: response })
    return event
}