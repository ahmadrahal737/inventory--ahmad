import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import { StatusBar } from "expo-status-bar";

const STORAGE_KEY = "@inventory_products";

const starterProducts = [
  {
    id: "1",
    name: "Samsung S22",
    qty: 10,
    price: 850,
    category: "Phones",
    barcode: "",
    image: null,
  },
  {
    id: "2",
    name: "Bluetooth Headphones",
    qty: 25,
    price: 35,
    category: "Accessories",
    barcode: "",
    image: null,
  },
];

function money(value) {
  return Number(value || 0).toFixed(2);
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("home");

  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState(null);

  const [form, setForm] = useState({
    name: "",
    qty: "0",
    price: "",
    category: "",
    barcode: "",
    image: null,
  });

  // Load saved products
  useEffect(() => {
    async function loadProducts() {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);

        if (saved) {
          setProducts(JSON.parse(saved));
        } else {
          setProducts(starterProducts);
        }
      } catch (error) {
        setProducts(starterProducts);
      }

      setLoaded(true);
    }

    loadProducts();
  }, []);

  // Save products
  useEffect(() => {
    if (loaded) {
      AsyncStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(products)
      );
    }
  }, [products, loaded]);

  const totalItems = products.reduce(
    (sum, product) => sum + Number(product.qty || 0),
    0
  );

  const totalValue = products.reduce(
    (sum, product) =>
      sum +
      Number(product.qty || 0) *
        Number(product.price || 0),
    0
  );

  const lowStock = products.filter(
    (product) => Number(product.qty) <= 5
  );

  const filteredProducts = useMemo(() => {
    const q = search.toLowerCase().trim();

    if (!q) {
      return products;
    }

    return products.filter(
      (product) =>
        product.name.toLowerCase().includes(q) ||
        (product.category || "")
          .toLowerCase()
          .includes(q) ||
        (product.barcode || "")
          .toLowerCase()
          .includes(q)
    );
  }, [products, search]);

  // Add product
  function openAdd() {
    setEditing(null);

    setForm({
      name: "",
      qty: "0",
      price: "",
      category: "",
      barcode: "",
      image: null,
    });

    setModal(true);
  }

  // Edit product
  function openEdit(product) {
    setEditing(product);

    setForm({
      name: product.name,
      qty: String(product.qty),
      price: String(product.price || ""),
      category: product.category || "",
      barcode: product.barcode || "",
      image: product.image || null,
    });

    setModal(true);
  }

  // Save product
  function saveProduct() {
    if (!form.name.trim()) {
      Alert.alert(
        "Missing name",
        "Please enter a product name."
      );

      return;
    }

    const product = {
      id: editing
        ? editing.id
        : Date.now().toString(),

      name: form.name.trim(),

      qty: Math.max(
        0,
        parseInt(form.qty || "0", 10) || 0
      ),

      price: Math.max(
        0,
        parseFloat(form.price || "0") || 0
      ),

      category: form.category.trim(),

      barcode: form.barcode.trim(),

      image: form.image,
    };

    if (editing) {
      setProducts((oldProducts) =>
        oldProducts.map((p) =>
          p.id === editing.id
            ? product
            : p
        )
      );
    } else {
      setProducts((oldProducts) => [
        product,
        ...oldProducts,
      ]);
    }

    setModal(false);
  }

  // Increase / decrease
  function changeQuantity(id, amount) {
    setProducts((oldProducts) =>
      oldProducts.map((product) =>
        product.id === id
          ? {
              ...product,
              qty: Math.max(
                0,
                Number(product.qty || 0) + amount
              ),
            }
          : product
      )
    );
  }

  // Delete
  function deleteProduct(id) {
    Alert.alert(
      "Delete product?",
      "This cannot be undone.",

      [
        {
          text: "Cancel",
          style: "cancel",
        },

        {
          text: "Delete",
          style: "destructive",

          onPress: () => {
            setProducts((oldProducts) =>
              oldProducts.filter(
                (product) => product.id !== id
              )
            );
          },
        },
      ]
    );
  }

  // Choose image
  async function pickImage() {
    const permission =
      await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert(
        "Permission needed",
        "Allow photo access."
      );

      return;
    }

    const result =
      await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 0.75,
        allowsEditing: true,
        aspect: [1, 1],
      });

    if (!result.canceled) {
      setForm((old) => ({
        ...old,
        image: result.assets[0].uri,
      }));
    }
  }

  // Camera
  async function takePhoto() {
    const permission =
      await ImagePicker.requestCameraPermissionsAsync();

    if (!permission.granted) {
      Alert.alert(
        "Permission needed",
        "Allow camera access."
      );

      return;
    }

    const result =
      await ImagePicker.launchCameraAsync({
        quality: 0.75,
        allowsEditing: true,
        aspect: [1, 1],
      });

    if (!result.canceled) {
      setForm((old) => ({
        ...old,
        image: result.assets[0].uri,
      }));
    }
  }

  if (!loaded) {
    return (
      <View style={styles.loading}>
        <Text style={styles.loadingTitle}>
          Inventory
        </Text>

        <Text>
          Loading...
        </Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />

      {/* HEADER */}

      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>
            Inventory
          </Text>

          <Text style={styles.headerSubtitle}>
            Smart stock management
          </Text>
        </View>

        <Text style={styles.headerIcon}>
          📦
        </Text>
      </View>

      {/* CONTENT */}

      <View style={styles.content}>

        {/* HOME */}

        {tab === "home" && (
          <ScrollView>

            <View style={styles.hero}>

              <Text style={styles.heroLabel}>
                TOTAL PRODUCTS
              </Text>

              <Text style={styles.heroNumber}>
                {products.length}
              </Text>

              <View style={styles.heroRow}>

                <View>
                  <Text style={styles.heroSmall}>
                    TOTAL QUANTITY
                  </Text>

                  <Text style={styles.heroMetric}>
                    {totalItems}
                  </Text>
                </View>

                <View>
                  <Text style={styles.heroSmall}>
                    STOCK VALUE
                  </Text>

                  <Text style={styles.heroMetric}>
                    ${money(totalValue)}
                  </Text>
                </View>

              </View>
            </View>

            <Text style={styles.sectionTitle}>
              Quick Actions
            </Text>

            <View style={styles.quickRow}>

              <Pressable
                style={styles.quickCard}
                onPress={openAdd}
              >
                <Text style={styles.quickIcon}>
                  ＋
                </Text>

                <Text>
                  Add Product
                </Text>
              </Pressable>

              <Pressable
                style={styles.quickCard}
                onPress={() =>
                  setTab("products")
                }
              >
                <Text style={styles.quickIcon}>
                  ▣
                </Text>

                <Text>
                  View Stock
                </Text>
              </Pressable>

            </View>

            <View style={styles.sectionRow}>
              <Text style={styles.sectionTitle}>
                Low Stock
              </Text>

              <Text style={styles.badge}>
                {lowStock.length}
              </Text>
            </View>

            {lowStock.map((product) => (
              <ProductRow
                key={product.id}
                product={product}
                onPlus={() =>
                  changeQuantity(
                    product.id,
                    1
                  )
                }
                onMinus={() =>
                  changeQuantity(
                    product.id,
                    -1
                  )
                }
                onEdit={() =>
                  openEdit(product)
                }
                onDelete={() =>
                  deleteProduct(
                    product.id
                  )
                }
              />
            ))}

          </ScrollView>
        )}

        {/* PRODUCTS */}

        {tab === "products" && (
          <View style={{ flex: 1 }}>

            <TextInput
              style={styles.search}
              value={search}
              onChangeText={setSearch}
              placeholder="Search product..."
            />

            <FlatList
              data={filteredProducts}
              keyExtractor={(item) =>
                item.id
              }
              renderItem={({ item }) => (
                <ProductRow
                  product={item}
                  onPlus={() =>
                    changeQuantity(
                      item.id,
                      1
                    )
                  }
                  onMinus={() =>
                    changeQuantity(
                      item.id,
                      -1
                    )
                  }
                  onEdit={() =>
                    openEdit(item)
                  }
                  onDelete={() =>
                    deleteProduct(
                      item.id
                    )
                  }
                />
              )}
            />

          </View>
        )}

        {/* REPORTS */}

        {tab === "reports" && (
          <ScrollView>

            <Text style={styles.pageTitle}>
              Reports
            </Text>

            <Stat
              title="Products"
              value={products.length}
            />

            <Stat
              title="Total Quantity"
              value={totalItems}
            />

            <Stat
              title="Stock Value"
              value={`$${money(totalValue)}`}
            />

            <Stat
              title="Low Stock"
              value={lowStock.length}
            />

          </ScrollView>
        )}

      </View>

      {/* NAVIGATION */}

      <View style={styles.bottom}>

        <Nav
          label="Home"
          active={tab === "home"}
          onPress={() => setTab("home")}
        />

        <Nav
          label="Products"
          active={tab === "products"}
          onPress={() => setTab("products")}
        />

        <Pressable
          style={styles.addButton}
          onPress={openAdd}
        >
          <Text style={styles.addButtonText}>
            ＋
          </Text>
        </Pressable>

        <Nav
          label="Reports"
          active={tab === "reports"}
          onPress={() => setTab("reports")}
        />

      </View>

      {/* ADD / EDIT MODAL */}

      <Modal
        visible={modal}
        animationType="
