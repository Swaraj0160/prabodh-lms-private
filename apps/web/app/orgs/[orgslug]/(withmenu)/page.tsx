import { Metadata } from 'next'
import { getOrganizationContextInfo } from '@services/organizations/orgs'
import { getOrgThumbnailMediaDirectory, getOrgOgImageMediaDirectory } from '@services/media/media'
import { getOrgSeoConfig, buildPageTitle } from '@/lib/seo/utils'
import { getServerCanonicalUrl } from '@/lib/seo/utils.server'
import HomeClient from './home-client'

type MetadataProps = {
  params: Promise<{ orgslug: string }>
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export async function generateMetadata(props: MetadataProps): Promise<Metadata> {
  const params = await props.params;
  // Get Org context information
  const org = await getOrganizationContextInfo(params.orgslug, {
    revalidate: 120,
    tags: ['organizations'],
  })

  const seoConfig = getOrgSeoConfig(org)
  const ogImageUrl = seoConfig.default_og_image
    ? getOrgOgImageMediaDirectory(org?.org_uuid, seoConfig.default_og_image)
    : null
  // Only build a thumbnail URL when a file is actually set — the media-directory
  // helpers below just interpolate the fileId into a path, so an empty/undefined
  // thumbnail_image previously produced a URL pointing at a directory with no
  // filename (".../thumbnails/"), which crawlers would fetch and fail on.
  const imageUrl = ogImageUrl || (org?.thumbnail_image
    ? getOrgThumbnailMediaDirectory(org?.org_uuid, org?.thumbnail_image)
    : null)
  const canonical = await getServerCanonicalUrl(params.orgslug, '/')
  const title = buildPageTitle('Home', org.name, seoConfig)
  const description = org.description || seoConfig.default_meta_description || ''

  // SEO
  return {
    title,
    description,
    robots: {
      index: true,
      follow: true,
      nocache: true,
      googleBot: {
        index: true,
        follow: true,
        'max-image-preview': 'large',
      },
    },
    alternates: {
      canonical,
    },
    ...(seoConfig.google_site_verification
      ? {
          verification: {
            google: seoConfig.google_site_verification,
          },
        }
      : {}),
    openGraph: {
      title,
      description,
      type: 'website',
      ...(imageUrl
        ? { images: [{ url: imageUrl, width: 800, height: 600, alt: org.name }] }
        : {}),
    },
    twitter: {
      card: imageUrl ? 'summary_large_image' : 'summary',
      title,
      description,
      ...(imageUrl ? { images: [imageUrl] } : {}),
      ...(seoConfig.twitter_handle && { site: seoConfig.twitter_handle }),
    },
  }
}

const OrgHomePage = async (params: any) => {
  const orgslug = (await params.params).orgslug
  return <HomeClient orgslug={orgslug} />
}

export default OrgHomePage
