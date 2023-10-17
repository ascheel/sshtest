package main

import (
	"log"
	"os"
	"strings"

	"golang.org/x/crypto/ssh"

	//"golang.org/x/crypto/ssh/knownhosts"
	"bufio"
	"fmt"
	"io"
	"path/filepath"

	//"strconv"
	"errors"
	"net"
	"syscall"
	"time"

	//"strings"
	"crypto/sha256"
	"encoding/json"
	"reflect"
)

type connectionInfo struct {
	Host     string
	User     string
	Port     string
	Key      string
	Password string
	ErrCode  int
	ErrText  string
	ErrRaw   error
}

func (connInfo *connectionInfo) SetDefaults() {
	connInfo.Port = "22"
}

func check(e error) {
	if e != nil {
		log.Fatal(e)
	}
}

func readSize(file *os.File) int64 {
	stat, err := file.Stat()
	check(err)
	return stat.Size()
}

func readFile(filename string) []byte {
	file, err := os.Open(filename)
	check(err)
	defer file.Close()
	// Read the file into a byte slice
	bs := make([]byte, readSize(file))
	_, err = bufio.NewReader(file).Read(bs)
	if err != nil && err != io.EOF {
		fmt.Println(err)
	}
	return bs
}

func sshConnect(connInfo *connectionInfo) (*ssh.Client, *ssh.Session, error) {
	var auth     []ssh.AuthMethod

	hostString := net.JoinHostPort(connInfo.Host, connInfo.Port)

	timeout, _ := time.ParseDuration("5s")
	if len(connInfo.Password) == 0 && len(connInfo.Key) == 0 {
		log.Fatalln("Both key and password are empty.  One must be provided.")
	} else if len(connInfo.Key) > 0 {
		keyData := readFile(connInfo.Key)
		pKey, keyErr := ssh.ParsePrivateKey(keyData)
		if keyErr != nil {
			log.Fatalln("Bad key: " + connInfo.Key)
		}
		auth = []ssh.AuthMethod{ssh.PublicKeys(pKey)}
	} else if len(connInfo.Password) > 0 {
		auth = []ssh.AuthMethod{ssh.Password(connInfo.Password)}
	}

	conf := &ssh.ClientConfig{
		User: connInfo.User,
		Auth: auth,
		Timeout: timeout,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}

	client, err := ssh.Dial(
		"tcp",
		hostString,
		conf,
	)
	if err != nil {
		return nil, nil, err
	}

	session, err := client.NewSession()
	if err != nil {
		return nil, nil, err
	}

	return client, session, nil
}

func sshCheck(err error) {
	if err != nil {
		if errors.Is(err, syscall.ECONNREFUSED) {
			fmt.Println("Connection refused.  CAUGHT IT.")
		}
	}
}

func tryConnect(connInfo *connectionInfo) bool {
	if len(connInfo.Key) == 0 && len(connInfo.Password) == 0 {
		log.Fatalln("No key or password provided.")
	} else if len(connInfo.Key) > 0 && len(connInfo.Password) > 0 {
		log.Fatalln("Application does not yet support passwords AND keys both.")
	} else if len(connInfo.Host) == 0 {
		log.Fatalln("No host provided.")
	}
	client, session, err := sshConnect(connInfo)
	connInfo.ErrRaw = err
	if err != nil {
		return false
	}

	command := "ls -l /"
	_, err = session.CombinedOutput(command)
	if err != nil {
		return false
	}
	if client == nil || session == nil {
		log.Fatal("You shouldn't get here.")
		return false
	}
	return true
}

func printStruct(connInfo *connectionInfo) {
	s := reflect.ValueOf(&connInfo).Elem().Elem()
	typeOfSSH := s.Type()
	//fmt.Println(typeOfSSH)
	for i := 0; i < s.NumField(); i++ {
	 	f := s.Field(i)
		//fmt.Println(f)
		fmt.Printf("%d: %s %s = %v\n", i, typeOfSSH.Field(i).Name, f.Type(), f.Interface())
	}
}

func getJson(connInfo *connectionInfo) string {
	type e struct {
		Host string
		Port string
		User string
		Password string
		Key string
		ErrCode int
		ErrText string
	}
	obj := e{
		Host: connInfo.Host,
		Port: connInfo.Port,
		User: connInfo.User,
		Password: sha256sum(connInfo.Password),
		Key: connInfo.Key,
		ErrCode: connInfo.ErrCode,
		ErrText: connInfo.ErrText,
	}
	jsonData, err := json.MarshalIndent(obj, "", "    ")
	if err != nil {
		log.Fatalln("Failed to parse json output.")
	}
	return string(jsonData)
}

func handleExit(connInfo *connectionInfo) {
	// 0 = success
	// 1 = authentication failure
	// 2 = timeout
	// 3 = connection refused
	// 4 = no route to host
	// 5 = can't resolve host

	printStruct(connInfo)
	fmt.Printf("%+v\n", connInfo)
	if connInfo.ErrRaw == nil {
		connInfo.ErrCode = 0
		connInfo.ErrText = "success"
	} else {
		if isAuthenticationError(connInfo.ErrRaw) {
			connInfo.ErrCode = 1
			connInfo.ErrText = "authentication failure"
		} else if os.IsTimeout(connInfo.ErrRaw) {
			connInfo.ErrCode = 2
			connInfo.ErrText = "timeout"
		} else if errors.Is(connInfo.ErrRaw, syscall.ECONNREFUSED) {
			connInfo.ErrCode = 3
			connInfo.ErrText = "connection refused"
		} else {
			connInfo.ErrCode = 255
			connInfo.ErrText = "Unknown"
		}
	}
	fmt.Println(getJson(connInfo))
	os.Exit(connInfo.ErrCode)
}

func isAuthenticationError(err error) bool {
	authKeywords := []string{
		"authentication failed",
		"invalid credentials",
		"unable to authenticate",
		"no supported methods remain",
	}
	for _, keyword := range authKeywords {
		if strings.Contains(strings.ToLower(string(fmt.Sprint(err))), strings.ToLower(keyword)) {
			return true
		}
	}
	return false
}

func sha256sum(text string) string {
	hasher := sha256.New()
	hasher.Write([]byte(text))
	return fmt.Sprintf("%x", hasher.Sum(nil))
}

func main() {
	homedir, err := os.UserHomeDir()
	check(err)

	sshdir := filepath.Join(homedir, ".ssh")
	pKeyPath := filepath.Join(sshdir, "id_rsa_ea")

	connInfo := connectionInfo {
		// Host: "192.168.1.15",
		Host: "10.43.1.1",
		// Host: "jump.dev-va6.ea.adobe.net",
		// Host: "192.168.1.2",
		User: "ea",
		Port: "22",
		Key: pKeyPath,
		Password: "",
	}

	tryConnect(&connInfo)
	handleExit(&connInfo)

	// if success {
	// 	fmt.Println("Successful.")
	// } else {
	// 	fmt.Println("Failure.")
	// 	var errCode uint8 = 0
	// 	var errText string
	// 	var e *net.OpError
	// 	// dial tcp 192.168.1.198:22: connect: connection refused
	// 	// ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain
	// 	// dial tcp 192.168.1.3:22: connect: no route to host
	// 	// dial tcp 172.217.14.78:22: i/o timeout

	// 	if errors.As(err, &e) {
	// 		errText = e.Err.Error()
	// 		if errText == "i/o timeout" {
	// 			errCode = 1
	// 		} else if errText == "connection refused" {
	// 			errCode = 2
	// 		} else if errText == "no route to host" {
	// 			errCode = 3
	// 		}
	// 		fmt.Println(errText)
	// 		fmt.Println(errCode)
	// 	}
	// 	//subs := strings.SplitN(err.Error(), ":", 1)
	// 	fmt.Println("Failure with ssh.Dial()")
	// 	fmt.Println(err)
	// }
}

