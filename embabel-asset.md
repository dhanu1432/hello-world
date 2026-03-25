what exactly is the meaning of Asset and Asset tracker in embabel, give examples
Fast
View as codemap
Asset and AssetTracker in Embabel
Asset represents structured data (documents, search results, generated content) associated with a conversation that can be tracked and referenced by the LLM Asset.kt:24-28 . It's an interface that extends LlmReferenceProvider, StableIdentified, and Timestamped Asset.kt:28 .

AssetTracker manages collections of assets throughout a conversation session AssetTracker.kt:23-26 . It provides methods to add assets and wrap tools to automatically track their outputs AssetTracker.kt:28-44 .

Key Examples
1. Creating and Tracking Assets
// Add an asset to the conversation tracker  
conversation.getAssetTracker().addAsset(myAsset);  
  
// Get all tracked assets  
List<Asset> trackedAssets = conversation.getAssetTracker().getAssets();
page.adoc:111-120

2. Message-Level Assets
AssistantMessage message = new AssistantMessage(  
    "Here's the report you requested",  
    null,  // name  
    null,  // awaitable  
    List.of(reportAsset, summaryAsset)  // assets  
);  
conversation.addMessage(message);
page.adoc:130-141

3. Asset Implementation Example
private class TestAsset(  
    override val id: String,  
    private val reference: LlmReference,  
    override val timestamp: Instant = Instant.now()  
) : Asset {  
    override fun reference(): LlmReference = reference  
    override fun persistent(): Boolean = false  
}
AssetViewSearchOperationsTest.kt:422-430

4. In-Memory Asset Tracker
class InMemoryAssetTracker(  
    initialAssets: Collection<Asset> = emptyList(),  
) : AssetTracker {  
    private val _assets: MutableSet<Asset> = initialAssets.toMutableSet()  
  
    override fun addAsset(asset: Asset) {  
        if (_assets.any { it.id == asset.id }) {  
            return  
        }  
        _assets += asset  
    }  
  
    override val assets: List<Asset>  
        get() = _assets.toList()  
}
InMemoryAssetTracker.kt:24-38

How Assets Work in Conversations
The Conversation interface provides a merged view of assets from both its AssetTracker and from messages Conversation.kt:41-55 :

Tracker assets appear first (explicit tracking takes priority)
Message assets follow in chronological order
Duplicates are removed by ID (tracker version wins) page.adoc:159-163
Automatic Asset Tracking with Tools
AssetTracker can wrap tools to automatically track their outputs AssetAddingTool.kt:36-44 :

// Wrap a tool so any outputs are tracked as assets  
Tool wrapped = assetTracker.addReturnedAssets(originalTool);  
  
// With filtering - only track certain assets  
Tool wrapped = assetTracker.addReturnedAssets(tool, asset ->   
    asset instanceof Report  // Only track Report assets  
);
page.adoc:1743-1756

Notes
Assets can be persistent or ephemeral Asset.kt:25-27
Assets provide LLM references, making them available as tools to the AI AssetView.kt:31-36
The Asset.asAsset() utility method can convert any LlmReferenceProvider to an Asset Asset.kt:32-39
Asset tracking is essential for RAG applications and for maintaining structured state across conversations
