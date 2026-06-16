import React, { useEffect, useState } from "react";
import { FlatList, Linking, SafeAreaView, ScrollView, Text, TouchableOpacity, View } from "react-native";

type DealSummary = {
  id: string;
  status: string;
  identity: { name: string; address?: string; asset_type?: string };
  assets: Array<{ id: string; name: string; coordinates?: { latitude: number; longitude: number } }>;
  documents: Array<{ id: string; name: string; storage_uri: string; document_type: string }>;
  alerts: Array<{ id: string; title: string; severity: string; status: string }>;
};

const API_BASE = "http://10.0.2.2:8765/api";

export default function App() {
  const [deals, setDeals] = useState<DealSummary[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/deals`).then((response) => response.json()).then(setDeals);
  }, []);

  const alerts = deals.flatMap((deal) => deal.alerts.map((alert) => ({ ...alert, dealName: deal.identity.name })));
  const mappedAssets = deals.flatMap((deal) =>
    deal.assets
      .filter((asset) => asset.coordinates)
      .map((asset) => ({ ...asset, dealName: deal.identity.name }))
  );
  const documents = deals.flatMap((deal) => deal.documents.map((document) => ({ ...document, dealName: deal.identity.name })));

  return (
    <SafeAreaView>
      <ScrollView>
        <View style={{ padding: 16 }}>
          <Text style={{ fontSize: 24, fontWeight: "700" }}>Real Estate Helm</Text>
          <Text>Alerts, watchlist review, quick approvals, mobile maps, and document preview.</Text>
        </View>

        <Text style={{ fontSize: 18, fontWeight: "700", paddingHorizontal: 16 }}>Alerts</Text>
        <FlatList
          data={alerts}
          scrollEnabled={false}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity style={{ borderTopWidth: 1, borderColor: "#ddd", padding: 16 }}>
              <Text style={{ fontWeight: "700" }}>{item.title}</Text>
              <Text>{item.dealName} | {item.severity} | {item.status}</Text>
            </TouchableOpacity>
          )}
        />

        <Text style={{ fontSize: 18, fontWeight: "700", paddingHorizontal: 16, paddingTop: 16 }}>Maps</Text>
        <FlatList
          data={mappedAssets}
          scrollEnabled={false}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={{ borderTopWidth: 1, borderColor: "#ddd", padding: 16 }}
              onPress={() => Linking.openURL(`geo:${item.coordinates?.latitude},${item.coordinates?.longitude}`)}
            >
              <Text style={{ fontWeight: "700" }}>{item.name}</Text>
              <Text>{item.dealName} | {item.coordinates?.latitude}, {item.coordinates?.longitude}</Text>
            </TouchableOpacity>
          )}
        />

        <Text style={{ fontSize: 18, fontWeight: "700", paddingHorizontal: 16, paddingTop: 16 }}>Document Preview</Text>
        <FlatList
          data={documents}
          scrollEnabled={false}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity style={{ borderTopWidth: 1, borderColor: "#ddd", padding: 16 }}>
              <Text style={{ fontWeight: "700" }}>{item.name}</Text>
              <Text>{item.dealName} | {item.document_type} | {item.storage_uri}</Text>
            </TouchableOpacity>
          )}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
