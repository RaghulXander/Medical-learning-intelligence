import rawLandingPageContent from '../../../content/landing-page.json';
import { parseLandingPageDocument } from './schema';

export const landingPageContent = parseLandingPageDocument(rawLandingPageContent);
