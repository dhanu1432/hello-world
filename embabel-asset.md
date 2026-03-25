I query a troubleshooting guide and use that to provide one troubleshooting step at a time. can that be tracked as an asset? I give this guide as part of prompt to LLM. what is the differnce between t...
Show full text
Fast
View as codemap
Yes, your troubleshooting guide can absolutely be tracked as an asset in Embabel. The key difference between treating it as an asset vs sending via prompt lies in persistence, reusability, and how the LLM can interact with it.

Asset vs Prompt: Key Differences
As an Asset
Tracked across the conversation - persists between messages Asset.kt:24-28
Available as LLM tools - can be queried and referenced AssetView.kt:31-36
Managed by AssetTracker - can be filtered, retrieved, and organized AssetTracker.kt:28-44
Deduplicated by ID - avoids duplicates across messages Conversation.kt:41-55
As Prompt Content
Ephemeral - only available for that specific LLM call
Not tracked - disappears after the interaction
Directly included - part of the prompt text itself
No tool access - LLM can't query or reference it later
Implementation Examples
1. Tracking as an Asset
// Create the troubleshooting guide as an asset  
Asset guideAsset = new TroubleshootingGuideAsset(  
    id = "wifi-troubleshooting-guide",  
    steps = listOf(  
        "Check if WiFi is enabled",  
        "Restart router",   
        "Update drivers",  
        "Contact ISP"  
    )  
);  
  
// Add to conversation tracker for persistence  
conversation.getAssetTracker().addAsset(guideAsset);  
  
// LLM can access it as a tool in subsequent messages  
var response = context.ai()  
    .withReferences(conversation.mostRecent(5).references())  
    .respond("What's the first troubleshooting step?");
2. Sending via Prompt
// Include directly in prompt (not tracked)  
var response = context.ai()  
    .withSystemPrompt("""  
        You are a troubleshooting assistant.   
        Use this guide: Check WiFi → Restart router → Update drivers → Contact ISP  
        Provide one step at a time.  
    """)  
    .respond("My WiFi isn't working");
Recommended Approach for Your Use Case
For providing troubleshooting steps one at a time, use an asset because:

State tracking - You can track which steps have been completed
Tool access - LLM can query specific steps or check progress
Persistence - Guide remains available across multiple troubleshooting sessions
Structured access - Better than parsing prompt text
@State  
record TroubleshootingState(  
    String guideId,  
    int currentStep,  
    List<String> completedSteps  
) implements Stage { ... }  
  
@Action(canRerun = true, trigger = UserMessage.class)  
void provideNextStep(Conversation conversation, ActionContext context) {  
    // Get the guide asset  
    TroubleshootingGuide guide = conversation.getAssetTracker()  
        .getAsset("wifi-troubleshooting-guide")  
        .orElseThrow();  
      
    // Get current state  
    TroubleshootingState state = getCurrentState(conversation);  
      
    // Provide next step  
    String nextStep = guide.getSteps().get(state.currentStep);  
      
    var response = new AssistantMessage(  
        "Step " + (state.currentStep + 1) + ": " + nextStep,  
        null, null,  
        List.of(guide) // Include guide as asset for reference  
    );  
      
    conversation.addMessage(response);  
}
Notes
Assets are ideal for structured content like guides that need to be referenced multiple times page.adoc:111-120
Use prompt content for simple, one-time instructions
Assets can be made persistent or ephemeral based on your needs Asset.kt:25-27
The Asset.asAsset() utility method can convert any LlmReferenceProvider to an Asset Asset.kt:32-39
---------------------------------------------------
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
