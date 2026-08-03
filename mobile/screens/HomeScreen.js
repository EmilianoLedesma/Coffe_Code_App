import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function HomeScreen({ navigation }) {

  return (
    <View style={styles.container}>

      <Text style={styles.title}>Coffee Code</Text>
      <Text style={styles.subtitle}>Panel principal</Text>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('Mesas')}
      >
        <Text style={styles.text}>Mesero</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('Caja')}
      >
        <Text style={styles.text}>Caja</Text>
      </TouchableOpacity>

    

      <TouchableOpacity
  style={styles.button}
  onPress={() => navigation.navigate('Cocina')}
>
  <Text style={styles.text}>Cocina</Text>
</TouchableOpacity>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    justifyContent: 'center',
    padding: 20
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 5
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 30,
    color: 'gray'
  },
  button: {
    backgroundColor: '#2E1B0F',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15
  },
  text: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center'
  }
});